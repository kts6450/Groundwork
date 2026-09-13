import pandas as pd
import pytest

from src.scoring.verify import SurvivalTables, grade, verify


def _tables() -> SurvivalTables:
    nation = pd.DataFrame(
        [
            {"category": "카페", "n": 1000, "surv_1y": 0.88, "surv_3y": 0.65},
            {"category": "한식", "n": 2000, "surv_1y": 0.87, "surv_3y": 0.67},
        ]
    )
    sido = pd.DataFrame(
        [
            {"sido": "서울특별시", "category": "카페", "n": 200, "surv_1y": 0.80, "surv_3y": 0.55},
        ]
    )
    sgg = pd.DataFrame(
        [
            {
                "sido": "서울특별시",
                "sgg": "종로구",
                "category": "카페",
                "n": 80,
                "surv_1y": 0.90,
                "surv_3y": 0.72,
            },
        ]
    )
    return SurvivalTables(nation=nation, sido=sido, sgg=sgg)


def test_grade_uses_five_point_gap() -> None:
    assert grade(0.70, 0.65) == "합격"
    assert grade(0.66, 0.65) == "주의"
    assert grade(0.60, 0.65) == "위험"


def test_verify_uses_sgg_when_available() -> None:
    result = verify("서울특별시 종로구 대학로11길 22", "커피숍", _tables())

    assert result["category"] == "카페"
    assert result["level"] == "시군구"
    assert result["surv_3y"] == pytest.approx(0.72)
    assert result["nation_3y"] == pytest.approx(0.65)
    assert result["grade"] == "합격"
    assert "종로구" in result["reason"]
    assert "72.0%" in result["reason"]


def test_verify_falls_back_to_sido_then_nation() -> None:
    tables = _tables()
    sido_only = verify("서울특별시 강남구 테헤란로 1", "커피숍", tables)
    assert sido_only["level"] == "시도"
    assert sido_only["grade"] == "위험"

    nation_only = verify("부산광역시 해운대구 구남로 1", "커피숍", tables)
    assert nation_only["level"] == "전국"
    assert nation_only["grade"] == "주의"


def test_verify_rejects_excluded_or_unknown_type() -> None:
    tables = _tables()
    assert verify("서울특별시 종로구 관철동 1", "편의점", tables)["error"] == "excluded"
    assert verify("서울특별시 종로구 관철동 1", "없는업태", tables)["error"] == "unmapped"


def test_verify_needs_parseable_address_for_local_lookup() -> None:
    result = verify("33-3", "커피숍", _tables())

    assert result["level"] == "전국"
    assert result["sido"] == ""
    assert result["grade"] == "주의"
