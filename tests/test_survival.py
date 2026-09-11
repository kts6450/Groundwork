import pandas as pd
import pytest

from src.scoring.survival import (
    CohortSpec,
    build_cohort,
    normalize_sido,
    survival_table,
)


def _frame(rows: list[dict]) -> pd.DataFrame:
    base = {
        "status": "영업/정상",
        "sido": "서울특별시",
        "sgg": "종로구",
        "category": "카페",
    }
    return pd.DataFrame([{**base, **row} for row in rows])


SPEC = CohortSpec(
    opened_from=pd.Timestamp("2015-01-01"),
    opened_to=pd.Timestamp("2020-12-31"),
    data_cutoff=pd.Timestamp("2024-12-31"),
)


def test_build_cohort_keeps_only_permits_in_window() -> None:
    df = _frame(
        [
            {"permit": "2014-12-31", "closed": None},
            {"permit": "2015-01-01", "closed": None},
            {"permit": "2020-12-31", "closed": None},
            {"permit": "2021-01-01", "closed": None},
        ]
    )
    df["permit"] = pd.to_datetime(df["permit"])
    df["closed"] = pd.to_datetime(df["closed"])

    cohort, dropped = build_cohort(df, SPEC)

    assert len(cohort) == 2
    assert dropped["permit_out_of_window"] == 2


def test_build_cohort_drops_closed_without_date_and_excluded_category() -> None:
    df = _frame(
        [
            {"permit": "2016-01-01", "closed": None, "status": "폐업"},
            {"permit": "2016-01-01", "closed": None, "category": "제외"},
            {"permit": "2016-01-01", "closed": None, "category": None},
            {"permit": "2016-01-01", "closed": "2015-06-01"},
            {"permit": "2016-01-01", "closed": None},
        ]
    )
    df["permit"] = pd.to_datetime(df["permit"])
    df["closed"] = pd.to_datetime(df["closed"])

    cohort, dropped = build_cohort(df, SPEC)

    assert len(cohort) == 1
    assert dropped["closed_status_without_date"] == 1
    assert dropped["category_excluded_or_unmapped"] == 2
    assert dropped["closed_before_permit"] == 1


def test_build_cohort_marks_survival_by_horizon() -> None:
    df = _frame(
        [
            {"permit": "2016-01-01", "closed": None},
            {"permit": "2016-01-01", "closed": "2016-06-30"},
            {"permit": "2016-01-01", "closed": "2017-01-01"},
            {"permit": "2016-01-01", "closed": "2018-12-31"},
            {"permit": "2016-01-01", "closed": "2019-01-02"},
        ]
    )
    df["permit"] = pd.to_datetime(df["permit"])
    df["closed"] = pd.to_datetime(df["closed"])

    cohort, _ = build_cohort(df, SPEC)

    assert cohort["surv_1y"].tolist() == [True, False, False, True, True]
    assert cohort["surv_3y"].tolist() == [True, False, False, False, True]


def test_spec_rejects_unobservable_horizon() -> None:
    with pytest.raises(ValueError):
        CohortSpec(
            opened_from=pd.Timestamp("2015-01-01"),
            opened_to=pd.Timestamp("2024-06-30"),
            data_cutoff=pd.Timestamp("2024-12-31"),
        )


def test_survival_table_rates_and_min_n() -> None:
    rows = [{"permit": "2016-01-01", "closed": None}] * 8 + [
        {"permit": "2016-01-01", "closed": "2017-06-01"},
        {"permit": "2016-01-01", "closed": "2016-03-01"},
    ]
    rows += [{"permit": "2016-01-01", "closed": None, "sgg": "중구"}] * 3
    df = _frame(rows)
    df["permit"] = pd.to_datetime(df["permit"])
    df["closed"] = pd.to_datetime(df["closed"])
    cohort, _ = build_cohort(df, SPEC)

    table, n_dropped = survival_table(cohort, by=["sido", "sgg", "category"], min_n=10)

    assert n_dropped == 1
    assert len(table) == 1
    row = table.iloc[0]
    assert row["sgg"] == "종로구"
    assert row["n"] == 10
    assert row["surv_1y"] == pytest.approx(0.9)
    assert row["surv_3y"] == pytest.approx(0.8)


def test_normalize_sido_merges_renamed_provinces() -> None:
    assert normalize_sido("강원도") == "강원특별자치도"
    assert normalize_sido("전라북도") == "전북특별자치도"
    assert normalize_sido("제주도") == "제주특별자치도"
    assert normalize_sido("경기도") == "경기도"
