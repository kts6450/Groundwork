"""백테스트: 과거 데이터로 만든 생존표가 이후 개업한 점포의 폐업을 가려내는가.

학습 코호트로 시군구×업종 생존표를 만들고, 그 뒤에 개업한 평가 코호트에
표의 값을 예측으로 붙여 실제 3년 생존과 비교한다. 평가 코호트의 폐업 정보는
학습에 쓰이지 않으므로 미래를 훔쳐보지 않는다.

비교 대상(베이스라인):
- 전체 평균: 업종·지역을 무시하고 전국 평균 하나로 예측
- 업종만: 전국 업종별 생존률
- 업종+지역: 시군구×업종 (없으면 시도, 전국 순으로 폴백) ← 검증기가 쓰는 것
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.scoring.survival import CohortSpec, build_cohort, survival_table

MIN_N = 10
THRESHOLD = 0.05


@dataclass(frozen=True)
class BacktestSpec:
    train: CohortSpec
    test: CohortSpec
    min_n: int = MIN_N
    horizon: int = 3

    def __post_init__(self) -> None:
        if self.train.opened_to >= self.test.opened_from:
            raise ValueError("평가 코호트는 학습 코호트보다 뒤에 열려야 한다")


def _tables(train_cohort: pd.DataFrame, min_n: int) -> dict[str, pd.DataFrame]:
    nation, _ = survival_table(train_cohort, by=["category"], min_n=min_n)
    with_region = train_cohort[train_cohort["sido"] != ""]
    sido, _ = survival_table(with_region, by=["sido", "category"], min_n=min_n)
    sgg, _ = survival_table(with_region, by=["sido", "sgg", "category"], min_n=min_n)
    return {"nation": nation, "sido": sido, "sgg": sgg}


def attach_predictions(
    test_cohort: pd.DataFrame, tables: dict[str, pd.DataFrame], horizon: int = 3
) -> pd.DataFrame:
    """평가 코호트에 세 가지 예측을 붙인다. level은 실제로 쓰인 표의 수준."""
    col = f"surv_{horizon}y"
    out = test_cohort.copy()

    nation = tables["nation"][["category", col, "n"]].rename(columns={col: "pred_category", "n": "n_nation"})
    sido = tables["sido"][["sido", "category", col, "n"]].rename(columns={col: "pred_sido", "n": "n_sido"})
    sgg = tables["sgg"][["sido", "sgg", "category", col, "n"]].rename(columns={col: "pred_sgg", "n": "n_sgg"})

    out = out.merge(nation, on="category", how="left")
    out = out.merge(sido, on=["sido", "category"], how="left")
    out = out.merge(sgg, on=["sido", "sgg", "category"], how="left")

    out["pred_overall"] = float(tables["nation"][col].mean())
    out["pred_region"] = out["pred_sgg"].fillna(out["pred_sido"]).fillna(out["pred_category"])
    out["level"] = "전국"
    out.loc[out["pred_sido"].notna(), "level"] = "시도"
    out.loc[out["pred_sgg"].notna(), "level"] = "시군구"
    out["n_used"] = out["n_sgg"].fillna(out["n_sido"]).fillna(out["n_nation"])
    return out


def assign_grades(frame: pd.DataFrame, threshold: float = THRESHOLD) -> pd.Series:
    """검증기와 같은 규칙: 지역 예측 − 전국 업종 예측."""
    diff = frame["pred_region"] - frame["pred_category"]
    grade = pd.Series("주의", index=frame.index, dtype="object")
    grade[diff >= threshold] = "합격"
    grade[diff <= -threshold] = "위험"
    return grade


def run_backtest(prepared: pd.DataFrame, spec: BacktestSpec) -> dict:
    """prepared: run_survival.prepare()의 출력. 학습·평가 코호트를 각각 만들고 예측을 붙인다."""
    train_cohort, train_dropped = build_cohort(prepared, spec.train)
    test_cohort, test_dropped = build_cohort(prepared, spec.test)

    tables = _tables(train_cohort, spec.min_n)
    scored = attach_predictions(test_cohort, tables, spec.horizon)
    scored["grade"] = assign_grades(scored)
    scored["survived"] = scored[f"surv_{spec.horizon}y"]

    return {
        "spec": spec,
        "train_cohort": train_cohort,
        "test_cohort": test_cohort,
        "train_dropped": train_dropped,
        "test_dropped": test_dropped,
        "tables": tables,
        "scored": scored,
    }
