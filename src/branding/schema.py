"""3단계 출력 스키마. `docs/interfaces.md` 4번이 기준이다."""

from __future__ import annotations

from src.branding.palette import is_valid_palette

BRAND_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["names", "palette", "logo_svg"],
    "properties": {
        "names": {
            "type": "array",
            "minItems": 2,
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "reason"],
                "properties": {
                    "name": {"type": "string", "description": "간판에 쓸 이름. 12자 이내"},
                    "reason": {"type": "string", "description": "컨셉과 어떻게 이어지는지 한 문장"},
                },
            },
        },
        "palette": {
            "type": "object",
            "additionalProperties": False,
            "required": ["primary", "secondary", "background"],
            "properties": {
                "primary": {"type": "string", "description": "#RRGGBB"},
                "secondary": {"type": "string", "description": "#RRGGBB"},
                "background": {"type": "string", "description": "#RRGGBB. 밝은 색"},
            },
        },
        "logo_svg": {
            "type": "string",
            "description": "viewBox='0 0 120 120'인 SVG 하나. script·외부 이미지·이벤트 속성 금지",
        },
    },
}

MAX_NAME_LEN = 20


class BrandError(ValueError):
    """브랜딩 결과가 형식을 못 지켰을 때."""


def validate_brand(payload: dict) -> dict:
    names = payload.get("names")
    if not isinstance(names, list) or not 2 <= len(names) <= 5:
        raise BrandError("names는 2~5개여야 한다")
    seen = set()
    for item in names:
        name = (item or {}).get("name", "").strip()
        if not name:
            raise BrandError("이름이 비었다")
        if len(name) > MAX_NAME_LEN:
            raise BrandError(f"이름이 너무 길다: {name!r}")
        if name in seen:
            raise BrandError(f"이름이 중복이다: {name!r}")
        seen.add(name)
        if not (item.get("reason") or "").strip():
            raise BrandError(f"{name!r}의 이유가 비었다")

    if not is_valid_palette(payload.get("palette")):
        raise BrandError("palette는 #RRGGBB 형식의 primary·secondary·background여야 한다")

    if not (payload.get("logo_svg") or "").strip():
        raise BrandError("logo_svg가 비었다")

    return payload
