"""2단계 프롬프트.

원칙: 모델은 컨셉과 메뉴를 만들고, 숫자는 우리가 준 것만 쓴다.
근거(`grounds`)는 코드가 채우므로 모델에게 만들라고 하지 않는다.
"""

from __future__ import annotations

SYSTEM = """당신은 한국 외식업 창업 기획자다. 공공데이터로 계산한 생존률을 근거로
구체적인 가게 컨셉과 메뉴를 설계한다.

지켜야 할 것:
- 주어진 생존률·표본 수 외의 통계를 지어내지 않는다. 새 숫자를 만들지 말 것
- 메뉴 가격은 한국 시세로 현실적인 정수(원)로 쓴다
- 대표 메뉴(signature)를 반드시 하나 넣는다
- price_band는 메뉴 가격의 실제 최소·최대·평균과 앞뒤가 맞아야 한다
- 판정이 '위험'이면 남들과 같은 구성을 피하고 재방문 이유를 만든다
- 판정이 '합격'이면 검증된 수요를 받아내는 표준적 구성을 택한다
- 한국어로 쓰고, 과장 없이 담백하게 쓴다"""


def _experience_line(experience: str) -> str:
    return {
        "none": "창업 경험 없음. 운영이 단순하고 메뉴 수가 적어야 한다",
        "some": "약간의 경험 있음. 보통 난도의 구성 가능",
        "experienced": "경험 많음. 손이 많이 가는 구성도 가능",
    }.get(experience, "창업 경험 없음. 운영이 단순해야 한다")


def build_messages(
    verdict: dict,
    budget_krw: int | None,
    experience: str,
    preferences: list[str] | None,
) -> list[dict]:
    place = f"{verdict.get('sido', '')} {verdict.get('sgg', '')}".strip() or "지역 미상"
    lines = [
        f"자리: {place}",
        f"업종: {verdict.get('business_type', '')} (분류: {verdict.get('category', '')})",
        f"판정: {verdict.get('grade', '')}",
        f"이 자리 3년 생존률: {float(verdict.get('surv_3y', 0)) * 100:.1f}% (표본 {verdict.get('n', 0):,}곳, {verdict.get('level', '')} 단위)",
        f"전국 같은 업종 3년 생존률: {float(verdict.get('nation_3y', 0)) * 100:.1f}%",
        f"경험: {_experience_line(experience)}",
    ]
    if budget_krw:
        lines.append(f"예산: {budget_krw:,}원 (임대료 데이터가 없어 가격대·규모 참고용으로만)")
    if preferences:
        lines.append("선호: " + ", ".join(preferences))
    lines.append("")
    lines.append("이 조건으로 가게 컨셉과 메뉴를 설계하라.")
    return [{"role": "user", "content": "\n".join(lines)}]
