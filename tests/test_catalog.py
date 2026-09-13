from src.scoring.catalog import explain, license_choices
from src.scoring.categories import EXCLUDE


def test_license_choices_skip_excluded_and_include_cafe() -> None:
    choices = license_choices()
    types = {row["business_type"] for row in choices}
    assert "커피숍" in types
    assert "한식" in types
    assert "편의점" not in types
    assert all(row["category"] != EXCLUDE for row in choices)


def test_explain_pass_and_exclude() -> None:
    text = explain(
        {
            "sido": "서울특별시",
            "sgg": "종로구",
            "category": "카페",
            "surv_3y": 0.703,
            "nation_3y": 0.646,
            "n": 883,
            "level": "시군구",
            "grade": "합격",
        }
    )
    assert "종로구" in text
    assert "70.3%" in text
    assert "합격" not in text or "높다" in text
    assert "높다" in text
    assert "카페는" in text
    assert explain({"error": "excluded"}) == "편의점·매점·푸드트럭처럼 고정 외식 점포가 아닌 업태는 검증하지 않는다."
    hanguk = explain(
        {
            "sido": "서울특별시",
            "sgg": "강남구",
            "category": "한식",
            "surv_3y": 0.596,
            "nation_3y": 0.669,
            "n": 4095,
            "level": "시군구",
            "grade": "위험",
        }
    )
    assert "한식은" in hanguk
    assert "한식는" not in hanguk
