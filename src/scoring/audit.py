"""업태 코드 사용 시기 감사.

인허가 업태는 시간이 지나며 폐지된다. 예를 들어 `통닭(치킨)`은 2016년경부터
신규 등록이 끊겼고, 치킨집은 `호프/통닭`으로 등록된다. 이런 업태를 그대로 두면
코호트 기간 초반 몇 달치만 모인 표본으로 생존률을 내게 되므로, 매 실행마다
검출해서 보고서에 경고로 남긴다.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# 코호트 마지막 N년 동안 신규 등록이 이 수 미만이면 '사실상 폐지'로 본다.
RECENT_YEARS = 3
RETIRED_MAX_RECENT = 100


@dataclass(frozen=True)
class UsageRow:
    business_type: str
    category: str
    total: int
    cohort: int
    recent: int
    first_year: int | None
    last_year: int | None

    @property
    def retired(self) -> bool:
        return self.recent < RETIRED_MAX_RECENT


def usage_by_type(
    prepared: pd.DataFrame,
    opened_from: pd.Timestamp,
    opened_to: pd.Timestamp,
    recent_years: int = RECENT_YEARS,
) -> list[UsageRow]:
    """업태별 전체·코호트·최근 등록 건수와 사용 연도 범위.

    prepared: business_type, category, permit 컬럼을 가진 프레임.
    매핑되지 않았거나 제외된 업종은 부르는 쪽에서 걸러 넣는다.
    """
    recent_from = opened_to - pd.DateOffset(years=recent_years)
    df = prepared[["business_type", "category", "permit"]].copy()
    in_cohort = (df["permit"] >= opened_from) & (df["permit"] <= opened_to)
    in_recent = (df["permit"] > recent_from) & (df["permit"] <= opened_to)

    rows: list[UsageRow] = []
    for (business_type, category), group in df.groupby(["business_type", "category"], dropna=False):
        years = group["permit"].dt.year.dropna()
        rows.append(
            UsageRow(
                business_type=str(business_type),
                category=str(category),
                total=len(group),
                cohort=int(in_cohort.loc[group.index].sum()),
                recent=int(in_recent.loc[group.index].sum()),
                first_year=int(years.min()) if not years.empty else None,
                last_year=int(years.max()) if not years.empty else None,
            )
        )
    rows.sort(key=lambda r: r.total, reverse=True)
    return rows


def retired_types(rows: list[UsageRow]) -> list[UsageRow]:
    """코호트 후반에 사실상 쓰이지 않는 업태. 표본이 원래 작은 것은 뺀다."""
    return [row for row in rows if row.retired and row.total >= RETIRED_MAX_RECENT]


def categories_at_risk(rows: list[UsageRow]) -> dict[str, float]:
    """묶음별로 '폐지된 업태에서 온 코호트 비율'. 1.0에 가까우면 그 묶음은 믿을 수 없다."""
    totals: dict[str, int] = {}
    retired: dict[str, int] = {}
    for row in rows:
        totals[row.category] = totals.get(row.category, 0) + row.cohort
        if row.retired:
            retired[row.category] = retired.get(row.category, 0) + row.cohort
    return {
        category: retired.get(category, 0) / total
        for category, total in totals.items()
        if total > 0 and retired.get(category, 0) > 0
    }
