import pandas as pd
import pytest

from src.monitor.changes import compare, describe, monthly_series
from src.monitor.timeline import build_timeline, open_count_at, slice_window


def _prepared(rows: list[dict]) -> pd.DataFrame:
    base = {"sido": "서울특별시", "sgg": "마포구", "category": "카페", "closed": None}
    df = pd.DataFrame([{**base, **row} for row in rows])
    df["permit"] = pd.to_datetime(df["permit"])
    df["closed"] = pd.to_datetime(df["closed"])
    return df


TIMELINE = build_timeline(
    _prepared(
        [
            {"permit": "2020-01-15"},
            {"permit": "2020-01-20"},
            {"permit": "2020-03-10", "closed": "2022-05-04"},
            {"permit": "2021-07-01", "closed": "2022-05-30"},
            {"permit": "2022-11-11"},
            {"permit": "2020-02-02", "sgg": "종로구"},
            {"permit": "2020-02-02", "category": "한식"},
        ]
    )
)


# --- 집계 ---


def test_timeline_counts_openings_and_closings_per_month() -> None:
    row = TIMELINE[(TIMELINE["sgg"] == "마포구") & (TIMELINE["month"] == "2020-01")].iloc[0]

    assert row["opened"] == 2
    assert row["closed"] == 0


def test_timeline_records_closings_in_the_month_they_happened() -> None:
    may = TIMELINE[(TIMELINE["sgg"] == "마포구") & (TIMELINE["month"] == "2022-05")].iloc[0]

    assert may["closed"] == 2
    assert may["opened"] == 0


def test_timeline_keeps_regions_and_categories_separate() -> None:
    assert set(TIMELINE["sgg"]) == {"마포구", "종로구"}
    assert set(TIMELINE["category"]) == {"카페", "한식"}


def test_timeline_drops_excluded_and_unmapped_rows() -> None:
    df = _prepared([{"permit": "2020-01-01", "category": "제외"}, {"permit": "2020-01-01", "category": None}])

    assert build_timeline(df).empty


def test_timeline_drops_rows_without_a_region() -> None:
    df = _prepared([{"permit": "2020-01-01", "sido": "", "sgg": ""}])

    assert build_timeline(df).empty


def test_open_count_is_cumulative_openings_minus_closings() -> None:
    assert open_count_at(TIMELINE, "서울특별시", "마포구", "카페", "2020-12") == 3
    assert open_count_at(TIMELINE, "서울특별시", "마포구", "카페", "2022-06") == 2
    assert open_count_at(TIMELINE, "서울특별시", "마포구", "카페", "2023-01") == 3


def test_slice_window_excludes_the_start_month_and_includes_the_end() -> None:
    window = slice_window(TIMELINE, "서울특별시", "마포구", "카페", "2020-01", "2020-03")

    assert window["month"].tolist() == ["2020-03"]


# --- 비교 ---


def test_compare_counts_changes_between_the_two_dates() -> None:
    result = compare(TIMELINE, "서울특별시", "마포구", "카페", "2020-01-31", "2022-12-31")

    assert result["same_category_opened"] == 3
    assert result["same_category_closed"] == 2
    assert result["net_change"] == 1
    assert result["from"] == "2020-01"
    assert result["to"] == "2022-12"


def test_compare_reports_open_counts_at_both_ends() -> None:
    result = compare(TIMELINE, "서울특별시", "마포구", "카페", "2020-01-31", "2022-12-31")

    assert result["open_count_then"] == 2
    assert result["open_count_now"] == 3


def test_compare_rejects_a_backwards_window() -> None:
    result = compare(TIMELINE, "서울특별시", "마포구", "카페", "2023-01-01", "2020-01-01")

    assert result["error"] == "as_of_before_computed_at"


def test_compare_handles_a_quiet_neighbourhood() -> None:
    result = compare(TIMELINE, "서울특별시", "마포구", "카페", "2023-01-01", "2023-06-01")

    assert result["same_category_opened"] == 0
    assert "없다" in result["message"]


def test_compare_accepts_month_only_dates() -> None:
    result = compare(TIMELINE, "서울특별시", "마포구", "카페", "2020-01", "2022-12")

    assert result["same_category_opened"] == 3


def test_compare_on_an_unknown_area_returns_zeros_not_an_error() -> None:
    result = compare(TIMELINE, "서울특별시", "없는구", "카페", "2020-01-01", "2023-01-01")

    assert result["same_category_opened"] == 0
    assert result["open_count_now"] == 0


# --- 문장 ---


def test_describe_says_competitors_grew() -> None:
    assert "늘었다" in describe("마포구", "카페", 4, 1, 3)


def test_describe_says_competitors_shrank() -> None:
    assert "줄었다" in describe("마포구", "카페", 1, 4, -3)


def test_describe_uses_the_right_korean_particle() -> None:
    assert "카페가" in describe("마포구", "카페", 1, 0, 1)
    assert "한식이" in describe("마포구", "한식", 1, 0, 1)


# --- 그래프용 ---


def test_monthly_series_is_ordered_and_only_covers_the_window() -> None:
    series = monthly_series(TIMELINE, "서울특별시", "마포구", "카페", "2020-01-01", "2022-12-31")
    months = [row["month"] for row in series]

    assert months == sorted(months)
    assert "2020-01" not in months
    assert all("2020-01" < m <= "2022-12" for m in months)


def test_month_parsing_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        compare(TIMELINE, "서울특별시", "마포구", "카페", "2020", "2022-12")


# --- 기준선 (집계 시작 이전 개업분) ---


def test_open_count_includes_shops_opened_before_the_window() -> None:
    df = _prepared([{"permit": "2005-01-01"}, {"permit": "2006-01-01"}, {"permit": "2020-01-01"}])
    timeline = build_timeline(df)

    assert open_count_at(timeline, "서울특별시", "마포구", "카페", "2020-12") == 3


def test_open_count_never_goes_negative_when_old_shops_close() -> None:
    df = _prepared(
        [
            {"permit": "2005-01-01", "closed": "2021-03-01"},
            {"permit": "2006-01-01", "closed": "2021-04-01"},
        ]
    )
    timeline = build_timeline(df)

    assert open_count_at(timeline, "서울특별시", "마포구", "카페", "2020-12") == 2
    assert open_count_at(timeline, "서울특별시", "마포구", "카페", "2022-01") == 0


def test_baseline_excludes_shops_already_closed_before_the_window() -> None:
    df = _prepared([{"permit": "2005-01-01", "closed": "2008-01-01"}])
    timeline = build_timeline(df)

    assert open_count_at(timeline, "서울특별시", "마포구", "카페", "2020-12") == 0


def test_baseline_row_is_not_counted_as_activity_in_any_window() -> None:
    df = _prepared([{"permit": "2005-01-01"}, {"permit": "2020-06-01"}])
    timeline = build_timeline(df)

    result = compare(timeline, "서울특별시", "마포구", "카페", "2010-01", "2021-01")

    assert result["same_category_opened"] == 1
    assert all(row["month"] != "0000-00" for row in monthly_series(timeline, "서울특별시", "마포구", "카페", "2010-01", "2021-01"))
