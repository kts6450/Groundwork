"""3단계: 컨셉 → 브랜드명·팔레트·로고 SVG.

2단계와 같은 구조다. 키가 있으면 Claude, 없거나 실패하면 규칙 기반 목업.
로고 SVG는 어느 쪽이든 `svg.sanitize_svg`를 통과한 것만 내보낸다.

상표 확인은 하지 않는다. 이름마다 `risk`에 사람이 확인해야 한다고 남긴다.
"""

from __future__ import annotations

import json
import os
import re

from src.branding.palette import PALETTES, palette_for
from src.branding.prompts import SYSTEM, build_messages
from src.branding.schema import BRAND_SCHEMA, BrandError, validate_brand
from src.branding.svg import SvgError, build_mock_logo, sanitize_svg

MODEL = "claude-opus-5"
MAX_TOKENS = 8000

TRADEMARK_NOTE = "같은 이름의 상표가 있는지 특허정보넷 키프리스에서 직접 확인해야 한다."

# 목업 이름 뼈대. 업종이 아니라 컨셉 톤에서 고른다.
NAME_SHAPES = (
    ("{keyword}의 자리", "컨셉의 핵심 단어를 그대로 쓴 이름"),
    ("{keyword}집", "부르기 쉬운 한 단어 이름"),
    ("오늘의 {keyword}", "매일 오는 곳이라는 뜻"),
)


def _keyword(concept: dict, category: str) -> str:
    """컨셉 한 줄에서 이름에 쓸 단어를 뽑는다. 없으면 업종명."""
    one_liner = concept.get("concept", {}).get("one_liner", "")
    match = re.search(r"에서 (.+?) 하나로", one_liner)
    if match:
        return match.group(1).strip()
    menu = concept.get("menu") or []
    if menu:
        return str(menu[0].get("name", category)).split()[0]
    return category


def build_mock_brand(concept: dict, category: str, preferences: list[str] | None = None) -> dict:
    keyword = _keyword(concept, category)
    palette = palette_for(category)
    names = [
        {"name": shape.format(keyword=keyword), "reason": reason, "risk": TRADEMARK_NOTE}
        for shape, reason in NAME_SHAPES
    ]
    return {"names": names, "palette": palette, "logo_svg": build_mock_logo(category, palette)}


def _client():
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic()


def _extract_json(response) -> dict:
    for block in response.content:
        if block.type == "text":
            return json.loads(block.text)
    raise BrandError("모델 응답에 text 블록이 없다")


def generate_with_llm(concept: dict, category: str, preferences: list[str] | None, client=None) -> dict:
    client = client or _client()
    if client is None:
        raise BrandError("ANTHROPIC_API_KEY가 없다")

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=build_messages(concept, category, preferences),
        output_config={"format": {"type": "json_schema", "schema": BRAND_SCHEMA}},
    )
    if getattr(response, "stop_reason", None) == "refusal":
        raise BrandError("모델이 생성을 거부했다")

    payload = validate_brand(_extract_json(response))
    payload["logo_svg"] = sanitize_svg(payload["logo_svg"])
    for item in payload["names"]:
        item["risk"] = TRADEMARK_NOTE  # 모델이 뭐라 썼든 상표 확인은 사람 몫
    return payload


def generate_brand(
    concept: dict,
    category: str,
    preferences: list[str] | None = None,
    client=None,
    use_llm: bool = True,
) -> dict:
    """3단계 진입점. 항상 같은 형식을 돌려주고 예외를 밖으로 내지 않는다."""
    if concept.get("error"):
        return {"error": concept["error"], "reason": concept.get("reason", "컨셉이 없어 브랜딩을 만들지 않는다.")}

    source = "mock"
    note = None
    payload = None

    if use_llm:
        try:
            payload = generate_with_llm(concept, category, preferences, client)
            source = "llm"
        except (BrandError, SvgError) as exc:
            note = str(exc)
        except Exception as exc:
            note = f"{type(exc).__name__}: {exc}"

    if payload is None:
        payload = validate_brand(build_mock_brand(concept, category, preferences))

    result = {"source": source, **payload}
    if source == "mock":
        result["note"] = note or "ANTHROPIC_API_KEY가 없어 규칙 기반으로 만들었다."
    return result


__all__ = ["PALETTES", "build_mock_brand", "generate_brand", "generate_with_llm"]
