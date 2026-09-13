import pandas as pd

from src.scoring.audit import categories_at_risk, retired_types, usage_by_type

FROM = pd.Timestamp("2015-01-01")
TO = pd.Timestamp("2023-06-30")


def _prepared(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["business_type", "category", "permit"])
    df["permit"] = pd.to_datetime(df["permit"])
    return df


def test_usage_counts_total_cohort_and_recent() -> None:
    rows = (
        [("한식", "한식", "2010-01-01")] * 2
        + [("한식", "한식", "2016-01-01")] * 3
        + [("한식", "한식", "2022-01-01")] * 4
    )
    usage = usage_by_type(_prepared(rows), FROM, TO)

    assert len(usage) == 1
    row = usage[0]
    assert (row.total, row.cohort, row.recent) == (9, 7, 4)
    assert (row.first_year, row.last_year) == (2010, 2022)


def test_retired_types_flags_type_that_stopped_being_used() -> None:
    rows = [("통닭(치킨)", "치킨·호프", "2015-03-01")] * 300
    rows += [("호프/통닭", "치킨·호프", "2022-01-01")] * 300
    usage = usage_by_type(_prepared(rows), FROM, TO)

    retired = retired_types(usage)

    assert [r.business_type for r in retired] == ["통닭(치킨)"]


def test_retired_types_ignores_small_types() -> None:
    rows = [("룸살롱", "주점", "2015-03-01")] * 3
    usage = usage_by_type(_prepared(rows), FROM, TO)

    assert retired_types(usage) == []


def test_categories_at_risk_reports_share_from_retired_types() -> None:
    rows = [("통닭(치킨)", "치킨", "2015-03-01")] * 300
    rows += [("커피숍", "카페", "2022-01-01")] * 300
    usage = usage_by_type(_prepared(rows), FROM, TO)

    at_risk = categories_at_risk(usage)

    assert at_risk == {"치킨": 1.0}
