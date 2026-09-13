"""화면·API가 쓰는 업태 목록과 전국 생존표."""

from __future__ import annotations

from src.scoring.categories import CATEGORIES, EXCLUDE, LICENSE_MAP
from src.scoring.verify import SurvivalTables


def license_choices() -> list[dict]:
    rows = []
    for name, bucket in LICENSE_MAP.items():
        if bucket == EXCLUDE:
            continue
        rows.append({"business_type": name, "category": bucket})
    order = {name: i for i, name in enumerate(CATEGORIES)}
    rows.sort(key=lambda row: (order.get(row["category"], 99), row["business_type"]))
    return rows


def nation_rates(tables: SurvivalTables) -> list[dict]:
    frame = tables.nation.sort_values("surv_3y", ascending=False)
    return [
        {
            "category": str(row.category),
            "n": int(row.n),
            "surv_1y": float(row.surv_1y),
            "surv_3y": float(row.surv_3y),
        }
        for row in frame.itertuples()
    ]


def explain(result: dict) -> str:
    error = result.get("error")
    if error == "unmapped":
        return "이 업태는 매핑표에 없다. 검증하지 않는다."
    if error == "excluded":
        return "편의점·매점·푸드트럭처럼 고정 외식 점포가 아닌 업태는 검증하지 않는다."
    if error:
        return "이 조건으로는 생존률을 계산하지 못했다."

    category = result["category"]
    eun = _topic_particle(category)
    local = f"{result['surv_3y'] * 100:.1f}"
    nation = f"{result['nation_3y'] * 100:.1f}"
    n = result["n"]
    level = result["level"]
    grade = result["grade"]
    place = _place(result, level)

    # 전국으로 내려간 경우 비교 대상이 자기 자신이라 '전국보다 높다'가 성립하지 않는다.
    if level == "전국":
        asked = f"{result.get('sido') or ''} {result.get('sgg') or ''}".strip()
        where = f"{asked}에는" if asked else "요청한 지역에는"
        return f"{where} 표본이 부족해 전국 값으로 답한다. 전국 {category} 3년 생존 {local}%, 표본 {n:,}곳."

    tail = f"{level} 표본 {n:,}곳."
    if grade == "합격":
        return f"{place} {category}{eun} 3년 생존 {local}%로 전국({nation}%)보다 높다. {tail}"
    if grade == "위험":
        return f"{place} {category}{eun} 3년 생존 {local}%로 전국({nation}%)보다 낮다. {tail}"
    return f"{place} {category}{eun} 3년 생존 {local}%로 전국({nation}%)과 비슷하다. {tail}"


def _place(result: dict, level: str) -> str:
    """표가 실제로 답한 범위. 시도로 내려갔는데 시군구 이름을 붙이면 오해를 부른다."""
    sido = result.get("sido") or ""
    sgg = result.get("sgg") or ""
    if level == "시군구":
        return f"{sido} {sgg}".strip()
    if level == "시도":
        return sido
    return "전국"


def _topic_particle(word: str) -> str:
    if not word:
        return "는"
    code = ord(word[-1])
    if 0xAC00 <= code <= 0xD7A3:
        return "은" if (code - 0xAC00) % 28 else "는"
    return "는"
