import json
from types import SimpleNamespace

import pytest

from src.monitor.assets import ASSET_KINDS, AssetError, build_mock_asset, generate_asset, validate_asset

PROJECT = {
    "category": "카페",
    "concept": {"concept": {"one_liner": "조용한 로스터리", "tone": ["차분한", "정제된"]}},
    "brand": {
        "names": [{"name": "머무름", "reason": "…", "risk": "…"}],
        "palette": {"primary": "#5b3a21", "secondary": "#c4841d", "background": "#f3ead7"},
    },
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


def test_mock_asset_is_valid_for_every_kind() -> None:
    for kind in ASSET_KINDS:
        validate_asset(build_mock_asset(PROJECT, kind))


def test_mock_asset_uses_the_saved_brand_name_and_colors() -> None:
    asset = build_mock_asset(PROJECT, "seasonal_menu")

    assert "머무름" in asset["title"]
    assert "#f3ead7" in asset["svg"]


def test_mock_asset_works_without_a_saved_brand() -> None:
    asset = build_mock_asset({"category": "한식"}, "sns_post")

    validate_asset(asset)
    assert asset["svg"].startswith("<svg")


def test_mock_asset_includes_the_context_line() -> None:
    asset = build_mock_asset(PROJECT, "seasonal_menu", "겨울 신메뉴 2종")

    assert "겨울 신메뉴 2종" in asset["body"]


def test_unknown_asset_kind_is_rejected() -> None:
    result = generate_asset(PROJECT, "billboard")

    assert result["error"] == "unknown_asset"


def test_validate_rejects_empty_fields() -> None:
    with pytest.raises(AssetError, match="body"):
        validate_asset({"title": "제목", "body": "  ", "svg": "<svg/>"})


def test_generate_falls_back_to_mock_without_a_key() -> None:
    result = generate_asset(PROJECT, "sns_post", use_llm=False)

    assert result["source"] == "mock"
    validate_asset(result)


def test_generate_sanitizes_the_model_svg() -> None:
    client = _fake_client(
        {
            "title": "겨울 한정",
            "body": "따뜻한 신메뉴가 나왔습니다.",
            "svg": '<svg viewBox="0 0 320 180"><rect x="0" y="0" width="10" height="10"/><script>x()</script></svg>',
        }
    )

    result = generate_asset(PROJECT, "seasonal_menu", client=client)

    assert result["source"] == "llm"
    assert "script" not in result["svg"]
    assert result["asset"] == "seasonal_menu"


def test_generate_falls_back_when_the_model_svg_is_unusable() -> None:
    client = _fake_client({"title": "겨울", "body": "본문", "svg": "<div>nope</div>"})

    result = generate_asset(PROJECT, "seasonal_menu", client=client)

    assert result["source"] == "mock"


def test_generate_falls_back_when_the_model_refuses() -> None:
    client = _fake_client(build_mock_asset(PROJECT, "sns_post"), stop_reason="refusal")

    result = generate_asset(PROJECT, "sns_post", client=client)

    assert result["source"] == "mock"
    assert "거부" in result["note"]


def test_generate_sends_the_saved_identity_to_the_model() -> None:
    client = _fake_client(build_mock_asset(PROJECT, "sns_post"))

    generate_asset(PROJECT, "sns_post", context="겨울 신메뉴", client=client)
    prompt = client.messages.kwargs["messages"][0]["content"]

    assert "머무름" in prompt
    assert "#5b3a21" in prompt
    assert "차분한" in prompt
    assert "겨울 신메뉴" in prompt
