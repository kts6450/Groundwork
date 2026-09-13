"""2단계 출력 스키마.

`docs/interfaces.md`의 3번 형식이 기준이다. LLM 응답과 목업이 같은 형식을 통과해야 한다.
JSON Schema는 Claude structured outputs에도 그대로 넘긴다.
"""

from __future__ import annotations

MENU_ROLES = ("signature", "core", "side")
EXPERIENCE_LEVELS = ("none", "some", "experienced")

# structured outputs와 검증에 같이 쓴다. grounds는 코드가 채우므로 여기에 없다.
CONCEPT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["concept", "menu", "price_band"],
    "properties": {
        "concept": {
            "type": "object",
            "additionalProperties": False,
            "required": ["one_liner", "target", "differentiator", "tone"],
            "properties": {
                "one_liner": {"type": "string", "description": "가게를 한 문장으로. 20자 안팎"},
                "target": {"type": "string", "description": "주 손님층을 구체적으로"},
                "differentiator": {
                    "type": "string",
                    "description": "생존률 수치를 근거로 한 전략. 숫자를 새로 지어내지 말 것",
                },
                "tone": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 4,
                    "description": "브랜드 톤 형용사",
                },
            },
        },
        "menu": {
            "type": "array",
            "minItems": 3,
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "price_krw", "role"],
                "properties": {
                    "name": {"type": "string"},
                    "price_krw": {"type": "integer", "minimum": 500, "maximum": 500000},
                    "role": {"type": "string", "enum": list(MENU_ROLES)},
                },
            },
        },
        "price_band": {
            "type": "object",
            "additionalProperties": False,
            "required": ["low_krw", "high_krw", "average_krw"],
            "properties": {
                "low_krw": {"type": "integer", "minimum": 500},
                "high_krw": {"type": "integer", "minimum": 500},
                "average_krw": {"type": "integer", "minimum": 500},
            },
        },
    },
}


class ConceptError(ValueError):
    """생성 결과가 형식을 못 지켰을 때."""


def validate_concept(payload: dict) -> dict:
    """형식과 값의 앞뒤를 확인한다. 통과하면 payload를 그대로 돌려준다."""
    for key in ("concept", "menu", "price_band"):
        if key not in payload:
            raise ConceptError(f"'{key}'가 없다")

    concept = payload["concept"]
    for key in ("one_liner", "target", "differentiator", "tone"):
        if not concept.get(key):
            raise ConceptError(f"concept.{key}가 비었다")
    if not isinstance(concept["tone"], list) or not 2 <= len(concept["tone"]) <= 4:
        raise ConceptError("concept.tone은 2~4개여야 한다")

    menu = payload["menu"]
    if not isinstance(menu, list) or not 3 <= len(menu) <= 8:
        raise ConceptError("menu는 3~8개여야 한다")
    roles = set()
    for item in menu:
        if item.get("role") not in MENU_ROLES:
            raise ConceptError(f"menu.role이 잘못됐다: {item.get('role')!r}")
        if not isinstance(item.get("price_krw"), int) or item["price_krw"] <= 0:
            raise ConceptError("menu.price_krw는 양의 정수여야 한다")
        if not item.get("name"):
            raise ConceptError("menu.name이 비었다")
        roles.add(item["role"])
    if "signature" not in roles:
        raise ConceptError("대표 메뉴(signature)가 하나는 있어야 한다")

    band = payload["price_band"]
    low, high, avg = band.get("low_krw"), band.get("high_krw"), band.get("average_krw")
    if not all(isinstance(v, int) for v in (low, high, avg)):
        raise ConceptError("price_band 값은 정수여야 한다")
    if not low <= avg <= high:
        raise ConceptError(f"price_band가 앞뒤가 안 맞는다: {low} <= {avg} <= {high}")

    prices = [item["price_krw"] for item in menu]
    if min(prices) < low or max(prices) > high:
        raise ConceptError("메뉴 가격이 price_band 밖에 있다")

    return payload
