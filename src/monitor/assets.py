"""7-2. 저장된 브랜드 정체성으로 만드는 홍보물.

개업 이후에도 앱을 쓸 이유가 이것이다. 저장된 이름·팔레트·톤을 프롬프트에 그대로
넣어, 매번 같은 브랜드로 보이게 한다.

2·3단계와 같은 구조다. 키가 있으면 Claude, 없거나 실패하면 규칙 기반 목업.
SVG는 어느 쪽이든 `branding.svg.sanitize_svg`를 통과한 것만 내보낸다.
"""

from __future__ import annotations

import json
import os

from src.branding.svg import SvgError, sanitize_svg

ASSET_KINDS = {
    "seasonal_menu": "시즌 메뉴 알림",
    "sns_post": "SNS 게시물",
    "event_banner": "이벤트 배너",
}

MODEL = "claude-opus-5"
MAX_TOKENS = 4000

ASSET_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "body", "svg"],
    "properties": {
        "title": {"type": "string", "description": "한 줄 제목. 16자 이내"},
        "body": {"type": "string", "description": "두세 문장. 가게 톤을 지킨다"},
        "svg": {
            "type": "string",
            "description": "viewBox='0 0 320 180'인 SVG. script·외부 이미지·on* 속성 금지",
        },
    },
}

SYSTEM = """당신은 한국 동네 가게의 홍보물을 만드는 사람이다. 주어진 브랜드 이름과 색,
톤을 그대로 지켜서 짧은 홍보 문구와 간단한 카드 이미지를 만든다.

- 과장하지 않는다. '최고', '유일' 같은 말을 쓰지 않는다
- 없는 할인율·수상 이력·재료 원산지를 지어내지 않는다
- svg는 viewBox="0 0 320 180" 하나. 단순한 도형과 짧은 글자만 쓴다
- script·style·image·foreignObject·on* 속성·외부 URL을 쓰지 않는다
- 색은 주어진 팔레트 값을 그대로 쓴다
- 한국어로 쓴다"""


class AssetError(ValueError):
    """홍보물 생성이 형식을 못 지켰을 때."""


def _brand_bits(project: dict) -> tuple[str, dict, list[str]]:
    brand = project.get("brand") or {}
    names = brand.get("names") or []
    name = names[0]["name"] if names else project.get("category", "우리 가게")
    palette = brand.get("palette") or {"primary": "#12100c", "secondary": "#c4841d", "background": "#f3ead7"}
    tone = ((project.get("concept") or {}).get("concept") or {}).get("tone") or []
    return name, palette, tone


def build_mock_asset(project: dict, asset: str, context: str = "") -> dict:
    """키 없이 만드는 카드. 글자는 SVG가 아니라 title·body로만 전달한다."""
    name, palette, _ = _brand_bits(project)
    label = ASSET_KINDS.get(asset, "알림")
    headline = context.strip() or label

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180">'
        f'<rect x="0" y="0" width="320" height="180" rx="16" fill="{palette["background"]}"/>'
        f'<rect x="0" y="0" width="8" height="180" fill="{palette["secondary"]}"/>'
        f'<circle cx="270" cy="46" r="22" fill="none" stroke="{palette["secondary"]}" stroke-width="3"/>'
        f'<path d="M32 132h256" stroke="{palette["primary"]}" stroke-width="2"/>'
        "</svg>"
    )
    return {
        "asset": asset,
        "title": f"{name} {label}",
        "body": f"{headline}. 자세한 내용은 매장에서 확인하세요.",
        "svg": sanitize_svg(svg),
    }


def validate_asset(payload: dict) -> dict:
    for key in ("title", "body", "svg"):
        if not (payload.get(key) or "").strip():
            raise AssetError(f"{key}가 비었다")
    if len(payload["title"]) > 40:
        raise AssetError("title이 너무 길다")
    return payload


def _client():
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic()


def _build_messages(project: dict, asset: str, context: str) -> list[dict]:
    name, palette, tone = _brand_bits(project)
    lines = [
        f"가게 이름: {name}",
        f"업종: {project.get('category', '')}",
        f"만들 것: {ASSET_KINDS.get(asset, asset)}",
        f"팔레트: primary {palette['primary']}, secondary {palette['secondary']}, background {palette['background']}",
    ]
    if tone:
        lines.append("톤: " + ", ".join(tone))
    if context:
        lines.append(f"이번 내용: {context}")
    lines.append("")
    lines.append("이 브랜드로 홍보물을 만들라.")
    return [{"role": "user", "content": "\n".join(lines)}]


def generate_asset(
    project: dict,
    asset: str,
    context: str = "",
    client=None,
    use_llm: bool = True,
) -> dict:
    """7-2 진입점. 항상 같은 형식을 돌려주고 예외를 밖으로 내지 않는다."""
    if asset not in ASSET_KINDS:
        return {"error": "unknown_asset", "reason": f"만들 수 있는 종류: {', '.join(ASSET_KINDS)}"}

    source = "mock"
    note = None
    payload = None
    client = client or (_client() if use_llm else None)

    if use_llm and client is not None:
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM,
                messages=_build_messages(project, asset, context),
                output_config={"format": {"type": "json_schema", "schema": ASSET_SCHEMA}},
            )
            if getattr(response, "stop_reason", None) == "refusal":
                raise AssetError("모델이 생성을 거부했다")
            text = next(b.text for b in response.content if b.type == "text")
            payload = validate_asset(json.loads(text))
            payload["svg"] = sanitize_svg(payload["svg"])
            payload["asset"] = asset
            source = "llm"
        except (AssetError, SvgError) as exc:
            note = str(exc)
        except Exception as exc:
            note = f"{type(exc).__name__}: {exc}"
    elif use_llm:
        note = "ANTHROPIC_API_KEY가 없어 규칙 기반으로 만들었다."

    if payload is None:
        payload = validate_asset(build_mock_asset(project, asset, context))

    result = {"source": source, **payload}
    if source == "mock":
        result["note"] = note or "규칙 기반으로 만들었다."
    return result
