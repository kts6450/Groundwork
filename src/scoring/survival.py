"""시군구 × 업종 생존표.

코호트: 인허가일자가 [opened_from, opened_to] 안인 점포.
생존(h년): 폐업일자가 없거나 인허가일자 + h년 이후에 폐업.
opened_to + 최대 h년 <= data_cutoff 여야 모든 점포가 h년을 관측 가능하다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

SIDO_ALIASES = {
    "강원도": "강원특별자치도",
    "전라북도": "전북특별자치도",
    "제주도": "제주특별자치도",
}

CLOSED_STATUS = "폐업"


@dataclass(frozen=True)
class CohortSpec:
    opened_from: pd.Timestamp
    opened_to: pd.Timestamp
    data_cutoff: pd.Timestamp
    horizons: tuple[int, ...] = field(default=(1, 3))

    def __post_init__(self) -> None:
        if self.opened_from > self.opened_to:
            raise ValueError("opened_from must be <= opened_to")
        last_observable = self.opened_to + pd.DateOffset(years=max(self.horizons))
        if last_observable > self.data_cutoff:
            raise ValueError(
                f"opened_to {self.opened_to.date()} + {max(self.horizons)}y exceeds "
                f"data_cutoff {self.data_cutoff.date()}; horizon not observable"
            )


def normalize_sido(sido: str) -> str:
    return SIDO_ALIASES.get(sido, sido)


def build_cohort(df: pd.DataFrame, spec: CohortSpec) -> tuple[pd.DataFrame, dict[str, int]]:
    """입력 컬럼: permit(datetime), closed(datetime), status(str), category(str|None), 그룹 컬럼.

    반환: (코호트 프레임 + surv_{h}y 불리언 컬럼, 제외 사유별 행 수)
    """
    dropped: dict[str, int] = {}

    in_window = df["permit"].notna() & (df["permit"] >= spec.opened_from) & (df["permit"] <= spec.opened_to)
    dropped["permit_out_of_window"] = int((~in_window).sum())
    cohort = df[in_window]

    closed_no_date = (cohort["status"] == CLOSED_STATUS) & cohort["closed"].isna()
    dropped["closed_status_without_date"] = int(closed_no_date.sum())
    cohort = cohort[~closed_no_date]

    closed_before_permit = cohort["closed"].notna() & (cohort["closed"] < cohort["permit"])
    dropped["closed_before_permit"] = int(closed_before_permit.sum())
    cohort = cohort[~closed_before_permit]

    bad_category = cohort["category"].isna() | (cohort["category"] == "제외")
    dropped["category_excluded_or_unmapped"] = int(bad_category.sum())
    cohort = cohort[~bad_category].copy()

    for h in spec.horizons:
        deadline = cohort["permit"] + pd.DateOffset(years=h)
        cohort[f"surv_{h}y"] = cohort["closed"].isna() | (cohort["closed"] > deadline)

    return cohort, dropped


def survival_table(
    cohort: pd.DataFrame,
    by: list[str],
    min_n: int = 10,
    horizons: tuple[int, ...] = (1, 3),
) -> tuple[pd.DataFrame, int]:
    """그룹별 n과 h년 생존률. n < min_n 그룹은 제외하고 그 수를 함께 돌려준다."""
    agg = {f"surv_{h}y": (f"surv_{h}y", "mean") for h in horizons}
    grouped = cohort.groupby(by, dropna=False).agg(n=("permit", "size"), **agg).reset_index()
    small = grouped["n"] < min_n
    table = grouped[~small].sort_values(by).reset_index(drop=True)
    return table, int(small.sum())
