import json
from types import SimpleNamespace

import pytest

from src.concept.generate import build_grounds, generate_concept
from src.concept.mock import build_mock_concept
from src.concept.schema import ConceptError, validate_concept

VERDICT = {
    "sido": "서울특별시",
    "sgg": "마포구",
    "business_type": "커피숍",
    "category": "카페",
    "level": "시군구",
    "n": 1499,
    "surv_1y": 0.8826,
    "surv_3y": 0.5710,
    "nation_3y": 0.6461,
    "diff_3y": -0.0750,
    "grade": "위험",
    "reason": "…",
    "evidence": "같은 '위험' 판정 50,722곳의 3년 생존은 59.6%였다.",
}


def _fake_client(payload: dict, stop_reason: str = "end_turn"):
    class Messages:
        def create(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text=json.dumps(payload, ensure_ascii=False))],
                stop_reason=stop_reason,
            )

    return SimpleNamespace(messages=Messages())


# --- 스키마 ---


def test_validate_rejects_price_band_that_contradicts_itself() -> None:
    payload = build_mock_concept(VERDICT)
    payload["price_band"]["average_krw"] = payload["price_band"]["high_krw"] + 1000

    with pytest.raises(ConceptError, match="앞뒤가"):
        validate_concept(payload)


def test_validate_rejects_menu_price_outside_band() -> None:
    payload = build_mock_concept(VERDICT)
    payload["menu"][0]["price_krw"] = payload["price_band"]["high_krw"] + 5000

    with pytest.raises(ConceptError, match="price_band 밖"):
        validate_concept(payload)


def test_validate_requires_a_signature_item() -> None:
    payload = build_mock_concept(VERDICT)
    for item in payload["menu"]:
        item["role"] = "core"

    with pytest.raises(ConceptError, match="대표 메뉴"):
        validate_concept(payload)


def test_validate_rejects_unknown_role() -> None:
    payload = build_mock_concept(VERDICT)
    payload["menu"][0]["role"] = "dessert"

    with pytest.raises(ConceptError, match="role"):
        validate_concept(payload)


# --- 목업 ---


def test_mock_is_valid_for_every_category() -> None:
    from src.scoring.categories import CATEGORIES

    for category in CATEGORIES:
        payload = build_mock_concept({**VERDICT, "category": category})
        validate_concept(payload)


def test_mock_is_deterministic() -> None:
    assert build_mock_concept(VERDICT) == build_mock_concept(VERDICT)


def test_mock_strategy_changes_with_grade() -> None:
    risky = build_mock_concept({**VERDICT, "grade": "위험"})["concept"]["differentiator"]
    good = build_mock_concept({**VERDICT, "grade": "합격"})["concept"]["differentiator"]

    assert risky != good
    assert "단골" in risky


def test_mock_scales_prices_with_budget() -> None:
    low = build_mock_concept(VERDICT, budget_krw=30_000_000)["price_band"]["average_krw"]
    high = build_mock_concept(VERDICT, budget_krw=200_000_000)["price_band"]["average_krw"]

    assert low < high


# --- 근거 ---


def test_grounds_come_from_the_verdict_numbers() -> None:
    grounds = build_grounds(VERDICT)

    assert any("57.1%" in g for g in grounds)
    assert any("64.6%" in g for g in grounds)
    assert any("1,499" in g for g in grounds)
    assert VERDICT["evidence"] in grounds


def test_grounds_name_the_sido_when_the_table_fell_back() -> None:
    grounds = build_grounds({**VERDICT, "level": "시도", "sgg": "진도군", "sido": "전라남도"})

    assert not any("진도군" in g for g in grounds)


# --- 진입점 ---


def test_generate_falls_back_to_mock_without_a_key() -> None:
    result = generate_concept(VERDICT, use_llm=False)

    assert result["source"] == "mock"
    assert "note" in result
    validate_concept(result)


def test_generate_uses_llm_result_when_the_call_succeeds() -> None:
    payload = build_mock_concept(VERDICT)
    payload["concept"]["one_liner"] = "모델이 쓴 문장"
    client = _fake_client(payload)

    result = generate_concept(VERDICT, client=client)

    assert result["source"] == "llm"
    assert result["concept"]["one_liner"] == "모델이 쓴 문장"


def test_generate_overwrites_grounds_the_model_invented() -> None:
    payload = build_mock_concept(VERDICT)
    payload["grounds"] = ["이 동네 카페 3년 생존 99.9%"]
    client = _fake_client(payload)

    result = generate_concept(VERDICT, client=client)

    assert "이 동네 카페 3년 생존 99.9%" not in result["grounds"]
    assert any("57.1%" in g for g in result["grounds"])


def test_generate_falls_back_when_the_model_returns_bad_shape() -> None:
    broken = build_mock_concept(VERDICT)
    broken["menu"] = []
    client = _fake_client(broken)

    result = generate_concept(VERDICT, client=client)

    assert result["source"] == "mock"
    validate_concept(result)


def test_generate_falls_back_when_the_model_refuses() -> None:
    client = _fake_client(build_mock_concept(VERDICT), stop_reason="refusal")

    result = generate_concept(VERDICT, client=client)

    assert result["source"] == "mock"
    assert "거부" in result["note"]


def test_generate_falls_back_when_the_call_raises() -> None:
    class Boom:
        def create(self, **kwargs):
            raise RuntimeError("network down")

    result = generate_concept(VERDICT, client=SimpleNamespace(messages=Boom()))

    assert result["source"] == "mock"
    assert "network down" in result["note"]


def test_generate_passes_through_verifier_errors() -> None:
    result = generate_concept({"error": "excluded", "reason": "검증 대상이 아니다."})

    assert result["error"] == "excluded"
    assert "menu" not in result


def test_generate_sends_the_schema_and_numbers_to_the_model() -> None:
    client = _fake_client(build_mock_concept(VERDICT))

    generate_concept(VERDICT, budget_krw=80_000_000, client=client)
    sent = client.messages.kwargs

    assert sent["model"] == "claude-opus-5"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    prompt = sent["messages"][0]["content"]
    assert "57.1%" in prompt
    assert "80,000,000원" in prompt
