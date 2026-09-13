"""LLM 키 없이 만드는 규칙 기반 컨셉.

목업이 있어야 API 키 없이도 화면이 뜨고 테스트가 돈다(CLAUDE.md 작업 규칙).
숫자는 검증 결과에서 가져오고, 문장은 업종별 표에서 고른다. 무작위를 쓰지 않아
같은 입력이면 같은 결과가 나온다.
"""

from __future__ import annotations

# 업종별 기준 가격(원)과 메뉴 뼈대. 시장 조사가 아니라 자리표시자다.
# 실제 가격 데이터를 넣기 전까지의 임시값이라는 점을 보고서·화면에 밝힌다.
CATEGORY_MENU: dict[str, tuple[str, list[tuple[str, int, str]]]] = {
    "카페": ("커피", [("드립 커피", 5000, "signature"), ("아메리카노", 4500, "core"), ("라떼", 5500, "core"), ("계절 디저트", 6500, "side")]),
    "디저트": ("구움과자", [("시그니처 케이크", 7500, "signature"), ("구움과자 세트", 6000, "core"), ("음료", 4500, "side")]),
    "한식": ("백반", [("제철 백반", 11000, "signature"), ("찌개 정식", 10000, "core"), ("계란말이", 6000, "side")]),
    "중식": ("짜장면", [("수제 짜장면", 9000, "signature"), ("짬뽕", 10000, "core"), ("탕수육(소)", 18000, "side")]),
    "일식": ("덮밥", [("사케동", 15000, "signature"), ("연어 덮밥", 14000, "core"), ("미소시루", 3000, "side")]),
    "양식": ("파스타", [("트러플 파스타", 18000, "signature"), ("토마토 파스타", 14000, "core"), ("수프", 6000, "side")]),
    "분식": ("떡볶이", [("즉석 떡볶이", 7000, "signature"), ("김밥", 4500, "core"), ("튀김", 5000, "side")]),
    "회·해산물": ("회", [("모둠회(소)", 45000, "signature"), ("물회", 15000, "core"), ("해산물 찜", 35000, "side")]),
    "고기구이": ("삼겹살", [("숙성 삼겹살", 16000, "signature"), ("목살", 15000, "core"), ("된장찌개", 5000, "side")]),
    "치킨·호프": ("치킨", [("후라이드", 18000, "signature"), ("양념치킨", 19000, "core"), ("생맥주 500", 5000, "side")]),
    "피자·버거": ("피자", [("시그니처 피자", 21000, "signature"), ("수제 버거", 12000, "core"), ("감자튀김", 5000, "side")]),
    "주점": ("안주", [("제철 안주", 19000, "signature"), ("마른 안주", 12000, "core"), ("소주·맥주", 5000, "side")]),
    "기타": ("대표 메뉴", [("대표 메뉴", 12000, "signature"), ("기본 메뉴", 9000, "core"), ("사이드", 5000, "side")]),
}

TARGET_BY_GRADE = {
    "합격": "이 상권에 이미 모여 있는 손님층",
    "주의": "주변 직장인과 거주민 중 재방문할 만한 층",
    "위험": "가격에 덜 민감하고 자주 오는 단골층",
}

STRATEGY_BY_GRADE = {
    "합격": "이 자리 {category} 3년 생존 {local:.1f}%는 전국 {nation:.1f}%보다 높다. 표준적인 구성으로 회전율을 높인다.",
    "주의": "이 자리 {category} 3년 생존 {local:.1f}%는 전국 {nation:.1f}%와 비슷하다. 대표 메뉴 하나로 기억에 남긴다.",
    "위험": "이 자리 {category} 3년 생존 {local:.1f}%는 전국 {nation:.1f}%보다 낮다. 신규 유입 대신 단골 재방문에 건다.",
}

TONE_BY_EXPERIENCE = {
    "none": ["단순한", "익히기 쉬운"],
    "some": ["안정적인", "실용적인"],
    "experienced": ["밀도 있는", "전문적인"],
}


def _budget_scale(budget_krw: int | None) -> float:
    """예산으로 가격대를 조금 움직인다. 임대료 데이터가 없어 대략적인 보정이다."""
    if not budget_krw:
        return 1.0
    if budget_krw < 50_000_000:
        return 0.9
    if budget_krw > 150_000_000:
        return 1.15
    return 1.0


def build_mock_concept(
    verdict: dict,
    budget_krw: int | None = None,
    experience: str = "none",
    preferences: list[str] | None = None,
) -> dict:
    category = verdict.get("category", "기타")
    grade = verdict.get("grade", "주의")
    local = float(verdict.get("surv_3y", 0.0)) * 100
    nation = float(verdict.get("nation_3y", 0.0)) * 100
    place = f"{verdict.get('sido', '')} {verdict.get('sgg', '')}".strip() or "이 자리"

    keyword, template = CATEGORY_MENU.get(category, CATEGORY_MENU["기타"])
    scale = _budget_scale(budget_krw)
    menu = [
        {"name": name, "price_krw": int(round(price * scale / 100) * 100), "role": role}
        for name, price, role in template
    ]
    prices = [item["price_krw"] for item in menu]
    tone = list(TONE_BY_EXPERIENCE.get(experience, TONE_BY_EXPERIENCE["none"]))
    if preferences:
        tone.append(preferences[0][:12])
    tone = tone[:4]

    one_liner = f"{place}에서 {keyword} 하나로 버티는 가게"
    return {
        "concept": {
            "one_liner": one_liner,
            "target": TARGET_BY_GRADE.get(grade, TARGET_BY_GRADE["주의"]),
            "differentiator": STRATEGY_BY_GRADE[grade].format(category=category, local=local, nation=nation),
            "tone": tone,
        },
        "menu": menu,
        "price_band": {
            "low_krw": min(prices),
            "high_krw": max(prices),
            "average_krw": int(sum(prices) / len(prices)),
        },
    }
