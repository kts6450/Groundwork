"""시군구 × 업종 × 연월 개·폐업 집계.

5단계(개업 이후)는 "내가 연 뒤로 주변이 어떻게 변했나"를 답해야 한다. 매번 인허가
290만 행을 훑을 수는 없으므로, 월 단위 집계표를 미리 만들어 둔다.

한 행 = (시도, 시군구, 업종, 연월)에서 그 달에 새로 연 곳과 닫은 곳의 수.
시점 T의 영업 중 점포 수는 T까지의 (개업 누적 − 폐업 누적)으로 구한다.
"""

from __future__ import annotations

import pandas as pd

MIN_MONTH = "2010-01"

# 집계 시작 이전에 열어 그때까지 살아 있던 점포를 담는 행의 month 값.
# 어떤 실제 연월보다 작아서 slice_window에는 절대 안 잡히고,
# open_count_at의 '이 달까지' 조건에는 항상 잡힌다.
BASELINE_MONTH = "0000-00"


def _month(series: pd.Series) -> pd.Series:
    return series.dt.to_period("M").astype(str)


def _baseline_rows(df: pd.DataFrame, min_month: str) -> pd.DataFrame:
    """집계 시작 직전에 이미 영업 중이던 점포 수.

    이 행이 없으면 2010년 이전 개업분이 '개업'으로 세어지지 않은 채 폐업만 잡혀
    누적 영업 수가 음수가 된다.
    """
    cutoff = pd.Period(min_month, freq="M").start_time - pd.Timedelta(days=1)
    alive = df["permit"].notna() & (df["permit"] <= cutoff) & (df["closed"].isna() | (df["closed"] > cutoff))
    counts = df[alive].groupby(["sido", "sgg", "category"]).size().reset_index(name="opened")
    counts["month"] = BASELINE_MONTH
    counts["closed"] = 0
    return counts[["sido", "sgg", "category", "month", "opened", "closed"]]


def build_timeline(prepared: pd.DataFrame, min_month: str = MIN_MONTH) -> pd.DataFrame:
    """prepared: run_survival.prepare()의 출력.

    반환 컬럼: sido, sgg, category, month, opened, closed
    업종이 없거나 제외된 행, 시군구를 못 읽은 행은 버린다.
    month가 BASELINE_MONTH인 행은 집계 시작 직전의 영업 중 점포 수다.
    """
    keep = (
        prepared["category"].notna()
        & (prepared["category"] != "제외")
        & (prepared["sido"] != "")
        & (prepared["sgg"] != "")
    )
    df = prepared[keep]

    opened = df[df["permit"].notna()].copy()
    opened["month"] = _month(opened["permit"])
    opened_counts = (
        opened.groupby(["sido", "sgg", "category", "month"]).size().reset_index(name="opened")
    )

    closed = df[df["closed"].notna()].copy()
    closed["month"] = _month(closed["closed"])
    closed_counts = (
        closed.groupby(["sido", "sgg", "category", "month"]).size().reset_index(name="closed")
    )

    timeline = opened_counts.merge(closed_counts, on=["sido", "sgg", "category", "month"], how="outer")
    timeline["opened"] = timeline["opened"].fillna(0).astype(int)
    timeline["closed"] = timeline["closed"].fillna(0).astype(int)
    timeline = timeline[timeline["month"] >= min_month]
    timeline = pd.concat([_baseline_rows(df, min_month), timeline], ignore_index=True)
    return timeline.sort_values(["sido", "sgg", "category", "month"]).reset_index(drop=True)


def slice_window(
    timeline: pd.DataFrame, sido: str, sgg: str, category: str, start_month: str, end_month: str
) -> pd.DataFrame:
    """(start_month, end_month] 구간. 시작 달은 빼고 끝 달은 포함한다."""
    mask = (
        (timeline["sido"] == sido)
        & (timeline["sgg"] == sgg)
        & (timeline["category"] == category)
        & (timeline["month"] > start_month)
        & (timeline["month"] <= end_month)
    )
    return timeline[mask]


def open_count_at(timeline: pd.DataFrame, sido: str, sgg: str, category: str, month: str) -> int:
    """해당 연월 말 기준 영업 중 점포 수. 기준선 행 덕분에 집계 시작 이전 개업분도 들어간다."""
    mask = (
        (timeline["sido"] == sido)
        & (timeline["sgg"] == sgg)
        & (timeline["category"] == category)
        & (timeline["month"] <= month)
    )
    window = timeline[mask]
    return int(window["opened"].sum() - window["closed"].sum())
