"""업종별 기본 팔레트.

목업 로고와, LLM이 팔레트를 못 주는 경우의 기본값이다.
화면(`web/src/app/globals.css`)의 종이 질감 배경과 어울리는 색으로 골랐다.
대비: 모든 primary는 배경 위에서 본문 텍스트로 쓰기에 충분히 어둡다.
"""

from __future__ import annotations

import re

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

PALETTES: dict[str, dict[str, str]] = {
    "카페": {"primary": "#5b3a21", "secondary": "#c4841d", "background": "#f3ead7"},
    "디저트": {"primary": "#8a3b52", "secondary": "#e0a3b4", "background": "#faf0ef"},
    "한식": {"primary": "#2f4f33", "secondary": "#c4841d", "background": "#f4efe2"},
    "중식": {"primary": "#9b1d2a", "secondary": "#d9a441", "background": "#f6ece2"},
    "일식": {"primary": "#1f3a5f", "secondary": "#8fb0c9", "background": "#f2f4f2"},
    "양식": {"primary": "#3a3a52", "secondary": "#b08968", "background": "#f5f2ec"},
    "분식": {"primary": "#c2453a", "secondary": "#f0b429", "background": "#fbf2e4"},
    "회·해산물": {"primary": "#17565e", "secondary": "#6fb3ad", "background": "#eef5f4"},
    "고기구이": {"primary": "#5c2a2a", "secondary": "#d07a3c", "background": "#f5ece4"},
    "치킨·호프": {"primary": "#7a4a12", "secondary": "#e0a325", "background": "#faf1de"},
    "피자·버거": {"primary": "#8a2f1f", "secondary": "#4a7c4e", "background": "#f7efe3"},
    "주점": {"primary": "#2b3a4a", "secondary": "#c4841d", "background": "#f1efe8"},
    "기타": {"primary": "#12100c", "secondary": "#c4841d", "background": "#f3ead7"},
}

DEFAULT = PALETTES["기타"]


def palette_for(category: str) -> dict[str, str]:
    return dict(PALETTES.get(category, DEFAULT))


def is_valid_palette(palette: object) -> bool:
    if not isinstance(palette, dict):
        return False
    return all(isinstance(palette.get(k), str) and HEX.match(palette[k]) for k in ("primary", "secondary", "background"))
