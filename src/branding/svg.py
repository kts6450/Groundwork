"""로고 SVG 살균과 생성.

LLM이 만든 SVG를 그대로 화면에 넣으면 스크립트가 실행될 수 있다. 화면에서
`dangerouslySetInnerHTML`로 렌더하기 전에 여기서 걸러야 한다. 허용 목록 방식이라
모르는 태그·속성은 통과하지 못한다.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"

ALLOWED_TAGS = {
    "svg", "g", "path", "circle", "ellipse", "rect", "line", "polyline",
    "polygon", "text", "tspan", "defs", "linearGradient", "radialGradient", "stop", "title",
}

ALLOWED_ATTRS = {
    "viewBox", "width", "height", "xmlns", "fill", "stroke", "stroke-width",
    "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "opacity", "fill-opacity",
    "stroke-opacity", "d", "cx", "cy", "r", "rx", "ry", "x", "y", "x1", "y1", "x2", "y2",
    "points", "transform", "font-family", "font-size", "font-weight", "text-anchor",
    "dominant-baseline", "letter-spacing", "offset", "stop-color", "stop-opacity",
    "gradientUnits", "id", "class",
}

# 속성값에 있으면 안 되는 것: 스크립트 URL, 외부 참조, CSS 표현식
_DANGEROUS_VALUE = re.compile(r"javascript:|data:text/html|<script|expression\(|url\s*\(\s*['\"]?https?:", re.I)

MAX_SVG_BYTES = 32_000


class SvgError(ValueError):
    """SVG가 비었거나, 형식이 아니거나, 살균 후 그릴 게 남지 않았을 때."""


def _local(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _clean_element(element: ET.Element) -> ET.Element | None:
    tag = _local(element.tag)
    if tag not in ALLOWED_TAGS:
        return None

    element.tag = tag
    kept = {}
    for name, value in element.attrib.items():
        attr = _local(name)
        if attr.startswith("on") or attr not in ALLOWED_ATTRS:
            continue
        if _DANGEROUS_VALUE.search(value):
            continue
        kept[attr] = value
    element.attrib = kept

    for child in list(element):
        cleaned = _clean_element(child)
        if cleaned is None:
            element.remove(child)
    return element


def sanitize_svg(raw: str) -> str:
    """허용 목록에 없는 태그·속성을 지운다. 그릴 게 남지 않으면 SvgError."""
    if not raw or not raw.strip():
        raise SvgError("SVG가 비었다")
    if len(raw.encode("utf-8")) > MAX_SVG_BYTES:
        raise SvgError(f"SVG가 너무 크다 ({len(raw.encode('utf-8')):,} 바이트)")

    text = raw.strip()
    start = text.find("<svg")
    if start == -1:
        raise SvgError("<svg> 요소가 없다")
    text = text[start:]

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise SvgError(f"SVG를 읽지 못했다: {exc}") from exc

    if _local(root.tag) != "svg":
        raise SvgError("최상위가 <svg>가 아니다")

    cleaned = _clean_element(root)
    if cleaned is None:
        raise SvgError("살균 후 남은 요소가 없다")
    if not list(cleaned):
        raise SvgError("그릴 도형이 없다")

    cleaned.set("xmlns", SVG_NS)
    if "viewBox" not in cleaned.attrib:
        cleaned.set("viewBox", "0 0 120 120")
    # 크기는 화면이 정한다. 고정 width/height는 레이아웃을 깬다.
    cleaned.attrib.pop("width", None)
    cleaned.attrib.pop("height", None)

    return ET.tostring(cleaned, encoding="unicode")


# 업종별 심볼. 목업 로고용 단순 도형이다.
CATEGORY_GLYPH: dict[str, str] = {
    "카페": '<circle cx="60" cy="62" r="26" fill="none" stroke="{primary}" stroke-width="5"/><path d="M86 52h10a9 9 0 0 1 0 18h-10" fill="none" stroke="{primary}" stroke-width="5"/><path d="M46 26v12M60 22v16M74 26v12" stroke="{secondary}" stroke-width="5" stroke-linecap="round"/>',
    "디저트": '<path d="M34 62h52l-6 34H40z" fill="none" stroke="{primary}" stroke-width="5" stroke-linejoin="round"/><path d="M34 62c0-14 12-24 26-24s26 10 26 24" fill="none" stroke="{secondary}" stroke-width="5"/>',
    "한식": '<ellipse cx="60" cy="66" rx="34" ry="14" fill="none" stroke="{primary}" stroke-width="5"/><path d="M26 66c0 16 15 26 34 26s34-10 34-26" fill="none" stroke="{primary}" stroke-width="5"/><path d="M60 24v22" stroke="{secondary}" stroke-width="5" stroke-linecap="round"/>',
    "중식": '<circle cx="60" cy="60" r="32" fill="none" stroke="{primary}" stroke-width="5"/><path d="M42 48h36M42 60h36M42 72h24" stroke="{secondary}" stroke-width="5" stroke-linecap="round"/>',
    "일식": '<rect x="30" y="44" width="60" height="32" rx="16" fill="none" stroke="{primary}" stroke-width="5"/><circle cx="60" cy="60" r="8" fill="{secondary}"/>',
    "양식": '<path d="M40 26v36a8 8 0 0 0 16 0V26" fill="none" stroke="{primary}" stroke-width="5"/><path d="M48 62v32" stroke="{primary}" stroke-width="5" stroke-linecap="round"/><path d="M78 26c8 6 8 22 0 30v38" fill="none" stroke="{secondary}" stroke-width="5" stroke-linecap="round"/>',
    "분식": '<path d="M32 78c10-8 18-8 28 0s18 8 28 0" fill="none" stroke="{primary}" stroke-width="5" stroke-linecap="round"/><circle cx="46" cy="48" r="9" fill="none" stroke="{secondary}" stroke-width="5"/><circle cx="74" cy="48" r="9" fill="none" stroke="{secondary}" stroke-width="5"/>',
    "회·해산물": '<path d="M26 60c14-18 40-18 54 0-14 18-40 18-54 0z" fill="none" stroke="{primary}" stroke-width="5"/><path d="M80 60l16-14v28z" fill="none" stroke="{secondary}" stroke-width="5" stroke-linejoin="round"/>',
    "고기구이": '<path d="M30 84h60" stroke="{primary}" stroke-width="5" stroke-linecap="round"/><path d="M40 84c0-14 8-22 20-22s20 8 20 22" fill="none" stroke="{primary}" stroke-width="5"/><path d="M48 26c-6 10 6 14 0 24M72 26c-6 10 6 14 0 24" fill="none" stroke="{secondary}" stroke-width="5" stroke-linecap="round"/>',
    "치킨·호프": '<path d="M36 44h30l-4 46H40z" fill="none" stroke="{primary}" stroke-width="5" stroke-linejoin="round"/><path d="M36 58h30" stroke="{secondary}" stroke-width="5"/><path d="M74 50c10 0 16 8 16 18s-6 18-16 18" fill="none" stroke="{primary}" stroke-width="5"/>',
    "피자·버거": '<path d="M60 24l32 60H28z" fill="none" stroke="{primary}" stroke-width="5" stroke-linejoin="round"/><circle cx="54" cy="62" r="5" fill="{secondary}"/><circle cx="70" cy="70" r="5" fill="{secondary}"/>',
    "주점": '<path d="M34 30h52L64 62v28" fill="none" stroke="{primary}" stroke-width="5" stroke-linejoin="round"/><path d="M46 92h36" stroke="{secondary}" stroke-width="5" stroke-linecap="round"/>',
    "기타": '<circle cx="60" cy="60" r="32" fill="none" stroke="{primary}" stroke-width="5"/><path d="M44 60h32" stroke="{secondary}" stroke-width="5" stroke-linecap="round"/>',
}


def build_mock_logo(category: str, palette: dict[str, str]) -> str:
    """업종 심볼 + 팔레트로 만든 목업 로고. LLM 없이도 화면에 뭔가 뜨게 한다."""
    glyph = CATEGORY_GLYPH.get(category, CATEGORY_GLYPH["기타"])
    body = glyph.format(primary=palette["primary"], secondary=palette["secondary"])
    svg = (
        f'<svg xmlns="{SVG_NS}" viewBox="0 0 120 120">'
        f'<rect x="0" y="0" width="120" height="120" rx="24" fill="{palette["background"]}"/>'
        f"{body}</svg>"
    )
    return sanitize_svg(svg)
