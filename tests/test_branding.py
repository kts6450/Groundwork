import json
from types import SimpleNamespace

import pytest

from src.branding.generate import TRADEMARK_NOTE, build_mock_brand, generate_brand
from src.branding.palette import is_valid_palette, palette_for
from src.branding.schema import BrandError, validate_brand
from src.branding.svg import SvgError, build_mock_logo, sanitize_svg
from src.concept.mock import build_mock_concept

VERDICT = {
    "sido": "서울특별시",
    "sgg": "마포구",
    "category": "카페",
    "grade": "위험",
    "surv_3y": 0.571,
    "nation_3y": 0.646,
    "n": 1499,
}
CONCEPT = build_mock_concept(VERDICT)


def _fake_client(payload: dict, stop_reason: str = "end_turn"):
    class Messages:
        def create(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text=json.dumps(payload, ensure_ascii=False))],
                stop_reason=stop_reason,
            )

    return SimpleNamespace(messages=Messages())


# --- SVG 살균 (보안 경계) ---


def test_sanitize_strips_script_elements() -> None:
    dirty = '<svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="20"/><script>alert(1)</script></svg>'

    clean = sanitize_svg(dirty)

    assert "script" not in clean
    assert "circle" in clean


def test_sanitize_strips_event_handler_attributes() -> None:
    dirty = '<svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="20" onload="alert(1)" onclick="x()"/></svg>'

    clean = sanitize_svg(dirty)

    assert "onload" not in clean
    assert "onclick" not in clean


def test_sanitize_strips_javascript_urls() -> None:
    dirty = '<svg viewBox="0 0 120 120"><path d="M0 0h10" fill="url(javascript:alert(1))"/></svg>'

    clean = sanitize_svg(dirty)

    assert "javascript" not in clean.lower()


def test_sanitize_drops_external_image_and_foreign_object() -> None:
    dirty = (
        '<svg viewBox="0 0 120 120">'
        '<image href="https://evil.example/x.png"/>'
        "<foreignObject><body>hi</body></foreignObject>"
        '<rect x="0" y="0" width="10" height="10"/></svg>'
    )

    clean = sanitize_svg(dirty)

    assert "image" not in clean
    assert "foreignObject" not in clean
    assert "rect" in clean


def test_sanitize_ignores_content_before_the_svg_element() -> None:
    clean = sanitize_svg('여기 로고입니다:\n<svg viewBox="0 0 120 120"><circle cx="1" cy="1" r="1"/></svg>')

    assert clean.startswith("<svg")


def test_sanitize_removes_fixed_size_so_layout_controls_it() -> None:
    clean = sanitize_svg('<svg viewBox="0 0 120 120" width="900" height="900"><circle cx="1" cy="1" r="1"/></svg>')

    assert "width=" not in clean
    assert "height=" not in clean


def test_sanitize_rejects_input_without_any_shape() -> None:
    with pytest.raises(SvgError, match="그릴 도형"):
        sanitize_svg('<svg viewBox="0 0 120 120"></svg>')


def test_sanitize_rejects_non_svg_and_malformed_input() -> None:
    with pytest.raises(SvgError, match="<svg>"):
        sanitize_svg("<div>hi</div>")
    with pytest.raises(SvgError, match="읽지 못"):
        sanitize_svg('<svg viewBox="0 0 1 1"><circle')
    with pytest.raises(SvgError, match="비었다"):
        sanitize_svg("   ")


def test_sanitize_rejects_oversized_svg() -> None:
    huge = '<svg viewBox="0 0 120 120">' + '<circle cx="1" cy="1" r="1"/>' * 2000 + "</svg>"

    with pytest.raises(SvgError, match="너무 크다"):
        sanitize_svg(huge)


# --- 팔레트 ---


def test_every_category_has_a_valid_palette() -> None:
    from src.scoring.categories import CATEGORIES

    for category in CATEGORIES:
        assert is_valid_palette(palette_for(category))


def test_is_valid_palette_rejects_bad_hex() -> None:
    assert not is_valid_palette({"primary": "red", "secondary": "#fff", "background": "#ffffff"})
    assert not is_valid_palette({"primary": "#123456"})
    assert not is_valid_palette("#123456")


# --- 스키마 ---


def test_validate_rejects_duplicate_names() -> None:
    payload = build_mock_brand(CONCEPT, "카페")
    payload["names"][1]["name"] = payload["names"][0]["name"]

    with pytest.raises(BrandError, match="중복"):
        validate_brand(payload)


def test_validate_rejects_overlong_name() -> None:
    payload = build_mock_brand(CONCEPT, "카페")
    payload["names"][0]["name"] = "아" * 30

    with pytest.raises(BrandError, match="너무 길다"):
        validate_brand(payload)


def test_validate_rejects_bad_palette() -> None:
    payload = build_mock_brand(CONCEPT, "카페")
    payload["palette"]["primary"] = "darkbrown"

    with pytest.raises(BrandError, match="palette"):
        validate_brand(payload)


# --- 목업 ---


def test_mock_logo_is_sanitized_for_every_category() -> None:
    from src.scoring.categories import CATEGORIES

    for category in CATEGORIES:
        svg = build_mock_logo(category, palette_for(category))
        assert svg.startswith("<svg")
        assert sanitize_svg(svg) == svg


def test_mock_brand_is_valid_and_deterministic() -> None:
    first = build_mock_brand(CONCEPT, "카페")
    validate_brand(first)

    assert first == build_mock_brand(CONCEPT, "카페")


def test_mock_names_pick_up_the_concept_keyword() -> None:
    names = [n["name"] for n in build_mock_brand(CONCEPT, "카페")["names"]]

    assert any("커피" in n for n in names)


# --- 진입점 ---


def test_generate_falls_back_to_mock_without_a_key() -> None:
    result = generate_brand(CONCEPT, "카페", use_llm=False)

    assert result["source"] == "mock"
    validate_brand(result)


def test_generate_sanitizes_the_svg_the_model_returned() -> None:
    payload = build_mock_brand(CONCEPT, "카페")
    payload["logo_svg"] = '<svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="20"/><script>steal()</script></svg>'
    client = _fake_client(payload)

    result = generate_brand(CONCEPT, "카페", client=client)

    assert result["source"] == "llm"
    assert "script" not in result["logo_svg"]


def test_generate_falls_back_when_the_model_svg_is_unusable() -> None:
    payload = build_mock_brand(CONCEPT, "카페")
    payload["logo_svg"] = "<div>not an svg</div>"
    client = _fake_client(payload)

    result = generate_brand(CONCEPT, "카페", client=client)

    assert result["source"] == "mock"


def test_generate_always_states_the_trademark_check_is_manual() -> None:
    payload = build_mock_brand(CONCEPT, "카페")
    for item in payload["names"]:
        item["risk"] = "상표 확인 완료, 문제 없음"
    client = _fake_client(payload)

    result = generate_brand(CONCEPT, "카페", client=client)

    assert all(item["risk"] == TRADEMARK_NOTE for item in result["names"])


def test_generate_falls_back_when_the_model_refuses() -> None:
    client = _fake_client(build_mock_brand(CONCEPT, "카페"), stop_reason="refusal")

    result = generate_brand(CONCEPT, "카페", client=client)

    assert result["source"] == "mock"
    assert "거부" in result["note"]


def test_generate_passes_through_upstream_errors() -> None:
    result = generate_brand({"error": "excluded", "reason": "검증 대상이 아니다."}, "카페")

    assert result["error"] == "excluded"
    assert "names" not in result
