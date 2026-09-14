"""시군구 업종 분포.

"이 동네는 무엇이 많은가"를 답한다. 원래 기획의 '업종 분포도'를 지도 없이
막대로 보여주기 위한 값이다.

핵심은 절대 수가 아니라 **전국 대비 비중**이다. 인구가 많은 구는 모든 업종이
많으므로, 절대 수만 보면 어디나 비슷해 보인다. 전국 업종 구성비와 비교해야
"여기는 유독 카페가 많다"가 드러난다.
"""

from __future__ import annotations

import pandas as pd

from src.monitor.changes import _particle

MIN_SHOPS = 5


def _open_counts(timeline: pd.DataFrame) -> pd.DataFrame:
    """시군구 × 업종별 현재 영업 중 점포 수. 기준선 행을 포함해 누적한다."""
    grouped = timeline.groupby(["sido", "sgg", "category"], as_index=False).agg(
        opened=("opened", "sum"), closed=("closed", "sum")
    )
    grouped["open_count"] = (grouped["opened"] - grouped["closed"]).clip(lower=0).astype(int)
    return grouped[["sido", "sgg", "category", "open_count"]]


def national_mix(timeline: pd.DataFrame) -> pd.DataFrame:
    """전국 업종 구성비."""
    counts = _open_counts(timeline).groupby("category", as_index=False)["open_count"].sum()
    total = counts["open_count"].sum()
    counts["nation_share"] = counts["open_count"] / total if total else 0.0
    return counts.rename(columns={"open_count": "nation_count"})


def distribution(timeline: pd.DataFrame, sido: str, sgg: str) -> dict:
    """한 시군구의 업종 구성과 전국 대비 배수.

    `ratio`가 1.5면 그 업종이 전국 평균보다 1.5배 몰려 있다는 뜻이다.
    """
    counts = _open_counts(timeline)
    local = counts[(counts["sido"] == sido) & (counts["sgg"] == sgg)]
    if local.empty:
        return {"error": "unknown_area", "reason": f"{sido} {sgg} 자료가 없다.", "sido": sido, "sgg": sgg}

    total = int(local["open_count"].sum())
    merged = local.merge(national_mix(counts_to_timeline(counts)), on="category", how="left")
    merged["share"] = merged["open_count"] / total if total else 0.0
    merged["ratio"] = merged.apply(
        lambda r: (r["share"] / r["nation_share"]) if r["nation_share"] else 0.0, axis=1
    )

    rows = [
        {
            "category": str(r.category),
            "open_count": int(r.open_count),
            "share": float(r.share),
            "nation_share": float(r.nation_share),
            "ratio": round(float(r.ratio), 3),
        }
        for r in merged.sort_values("open_count", ascending=False).itertuples()
    ]
    dense = [r for r in rows if r["open_count"] >= MIN_SHOPS]
    dense.sort(key=lambda r: r["ratio"], reverse=True)

    return {
        "sido": sido,
        "sgg": sgg,
        "total": total,
        "rows": rows,
        "most_dense": dense[0] if dense else None,
        "least_dense": dense[-1] if dense else None,
    }


def counts_to_timeline(counts: pd.DataFrame) -> pd.DataFrame:
    """`_open_counts` 결과를 다시 집계 가능한 모양으로. national_mix 재사용용."""
    out = counts.rename(columns={"open_count": "opened"}).copy()
    out["closed"] = 0
    return out


def describe(result: dict) -> str:
    if result.get("error") or not result.get("most_dense"):
        return ""
    top = result["most_dense"]
    return (
        f"{result['sgg']}에는 음식점·카페가 {result['total']:,}곳 있고, "
        f"그중 {top['category']}{_particle(top['category'])} 전국 평균보다 {top['ratio']:.1f}배 몰려 있다."
    )
