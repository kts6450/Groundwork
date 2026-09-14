import pandas as pd
import pytest

from src.monitor.distribution import describe, distribution, national_mix

# 마포구: 카페 60, 한식 40  (카페 비중 60%)
# 종로구: 카페 20, 한식 80  (카페 비중 20%)
# 전국:   카페 80, 한식 120 (카페 비중 40%)
TIMELINE = pd.DataFrame(
    [
        {"sido": "서울특별시", "sgg": "마포구", "category": "카페", "month": "0000-00", "opened": 60, "closed": 0},
        {"sido": "서울특별시", "sgg": "마포구", "category": "한식", "month": "0000-00", "opened": 40, "closed": 0},
        {"sido": "서울특별시", "sgg": "종로구", "category": "카페", "month": "0000-00", "opened": 20, "closed": 0},
        {"sido": "서울특별시", "sgg": "종로구", "category": "한식", "month": "0000-00", "opened": 80, "closed": 0},
    ]
)


def test_national_mix_sums_to_one() -> None:
    mix = national_mix(TIMELINE)

    assert mix["nation_share"].sum() == pytest.approx(1.0)


def test_national_mix_uses_counts_across_every_area() -> None:
    mix = national_mix(TIMELINE).set_index("category")

    assert mix.loc["카페", "nation_count"] == 80
    assert mix.loc["카페", "nation_share"] == pytest.approx(0.4)


def test_distribution_reports_local_share_and_ratio() -> None:
    result = distribution(TIMELINE, "서울특별시", "마포구")
    by_category = {row["category"]: row for row in result["rows"]}

    assert result["total"] == 100
    assert by_category["카페"]["share"] == pytest.approx(0.6)
    assert by_category["카페"]["ratio"] == pytest.approx(1.5)


def test_ratio_below_one_means_less_dense_than_the_country() -> None:
    result = distribution(TIMELINE, "서울특별시", "종로구")
    by_category = {row["category"]: row for row in result["rows"]}

    assert by_category["카페"]["ratio"] == pytest.approx(0.5)
    assert by_category["한식"]["ratio"] == pytest.approx(4 / 3, abs=1e-3)  # ratio는 소수 3자리로 반올림한다


def test_most_and_least_dense_are_picked_by_ratio() -> None:
    result = distribution(TIMELINE, "서울특별시", "마포구")

    assert result["most_dense"]["category"] == "카페"
    assert result["least_dense"]["category"] == "한식"


def test_rows_are_ordered_by_absolute_count() -> None:
    rows = distribution(TIMELINE, "서울특별시", "종로구")["rows"]

    assert [r["category"] for r in rows] == ["한식", "카페"]


def test_tiny_categories_do_not_win_the_headline() -> None:
    timeline = pd.concat(
        [
            TIMELINE,
            pd.DataFrame(
                [{"sido": "서울특별시", "sgg": "마포구", "category": "디저트", "month": "0000-00", "opened": 1, "closed": 0}]
            ),
        ]
    )

    result = distribution(timeline, "서울특별시", "마포구")

    assert result["most_dense"]["category"] != "디저트"


def test_closed_shops_are_subtracted() -> None:
    timeline = pd.concat(
        [
            TIMELINE,
            pd.DataFrame(
                [{"sido": "서울특별시", "sgg": "마포구", "category": "카페", "month": "2024-01", "opened": 0, "closed": 10}]
            ),
        ]
    )

    result = distribution(timeline, "서울특별시", "마포구")
    by_category = {row["category"]: row for row in result["rows"]}

    assert by_category["카페"]["open_count"] == 50


def test_unknown_area_returns_an_error_not_an_exception() -> None:
    result = distribution(TIMELINE, "서울특별시", "없는구")

    assert result["error"] == "unknown_area"


def test_describe_names_the_densest_category() -> None:
    text = describe(distribution(TIMELINE, "서울특별시", "마포구"))

    assert "마포구" in text
    assert "카페" in text
    assert "1.5배" in text


def test_describe_uses_the_right_korean_particle() -> None:
    timeline = pd.DataFrame(
        [
            {"sido": "서울특별시", "sgg": "마포구", "category": "일식", "month": "0000-00", "opened": 60, "closed": 0},
            {"sido": "서울특별시", "sgg": "마포구", "category": "카페", "month": "0000-00", "opened": 10, "closed": 0},
            {"sido": "서울특별시", "sgg": "종로구", "category": "카페", "month": "0000-00", "opened": 90, "closed": 0},
        ]
    )

    assert "일식이" in describe(distribution(timeline, "서울특별시", "마포구"))


def test_describe_is_empty_for_an_unknown_area() -> None:
    assert describe(distribution(TIMELINE, "서울특별시", "없는구")) == ""
