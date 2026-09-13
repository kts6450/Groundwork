"""2단계: 검증 결과 + 사용자 조건 → 컨셉·메뉴·가격대.

키가 있으면 Claude로 생성하고, 없거나 실패하면 규칙 기반 목업으로 내려간다.
어느 쪽이든 같은 형식(`docs/interfaces.md` 3번)이고, `source`가 어느 쪽인지 말해 준다.

`grounds`는 LLM이 아니라 코드가 검증 결과에서 채운다. 근거 숫자를 모델이 지어내면
이 서비스의 차별점이 무너지기 때문이다.
"""

from __future__ import annotations

import json
import os

from src.concept.mock import build_mock_concept
from src.concept.prompts import build_messages, SYSTEM
from src.concept.schema import CONCEPT_SCHEMA, ConceptError, validate_concept

MODEL = "claude-opus-5"
MAX_TOKENS = 8000


def build_grounds(verdict: dict) -> list[str]:
    """근거 문장. 검증 결과의 숫자만 쓴다."""
    place = f"{verdict.get('sido', '')} {verdict.get('sgg', '')}".strip()
    category = verdict.get("category", "")
    grounds = []
    if "surv_3y" in verdict:
        level = verdict.get("level", "")
        scope = place if level == "시군구" else (verdict.get("sido") or "전국")
        grounds.append(f"{scope} {category} 3년 생존 {verdict['surv_3y'] * 100:.1f}% (표본 {verdict.get('n', 0):,}곳)")
    if "nation_3y" in verdict:
        grounds.append(f"전국 {category} 3년 생존 {verdict['nation_3y'] * 100:.1f}%")
    if verdict.get("grade"):
        grounds.append(f"판정 {verdict['grade']}")
    if verdict.get("evidence"):
        grounds.append(verdict["evidence"])
    return grounds


def _client():
    """anthropic SDK 클라이언트. 키나 패키지가 없으면 None."""
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic()


def _extract_json(response) -> dict:
    """structured outputs를 켰으므로 text 블록이 곧 JSON이다."""
    for block in response.content:
        if block.type == "text":
            return json.loads(block.text)
    raise ConceptError("모델 응답에 text 블록이 없다")


def generate_with_llm(
    verdict: dict,
    budget_krw: int | None,
    experience: str,
    preferences: list[str] | None,
    client=None,
) -> dict:
    """Claude 호출. 실패는 예외로 올린다. 폴백은 generate_concept이 맡는다."""
    client = client or _client()
    if client is None:
        raise ConceptError("ANTHROPIC_API_KEY가 없다")

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=build_messages(verdict, budget_krw, experience, preferences),
        output_config={"format": {"type": "json_schema", "schema": CONCEPT_SCHEMA}},
    )
    if getattr(response, "stop_reason", None) == "refusal":
        raise ConceptError("모델이 생성을 거부했다")
    return validate_concept(_extract_json(response))


def generate_concept(
    verdict: dict,
    budget_krw: int | None = None,
    experience: str = "none",
    preferences: list[str] | None = None,
    client=None,
    use_llm: bool = True,
) -> dict:
    """2단계 진입점. 항상 같은 형식을 돌려주고, 실패해도 예외를 밖으로 내지 않는다."""
    if verdict.get("error"):
        return {"error": verdict["error"], "reason": verdict.get("reason", "검증 결과가 없어 컨셉을 만들지 않는다.")}

    source = "mock"
    note = None
    payload = None

    if use_llm:
        try:
            payload = generate_with_llm(verdict, budget_krw, experience, preferences, client)
            source = "llm"
        except ConceptError as exc:
            note = str(exc)
        except Exception as exc:  # 네트워크·SDK 오류에도 화면은 떠야 한다
            note = f"{type(exc).__name__}: {exc}"

    if payload is None:
        payload = validate_concept(build_mock_concept(verdict, budget_krw, experience, preferences))

    result = {"source": source, **payload, "grounds": build_grounds(verdict)}
    if source == "mock":
        result["note"] = note or "ANTHROPIC_API_KEY가 없어 규칙 기반으로 만들었다. 가격은 자리표시자다."
    return result
