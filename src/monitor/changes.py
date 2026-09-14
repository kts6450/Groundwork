"""저장된 프로젝트 + 새 시점 → 상권 변화.

`docs/interfaces.md` 7-1의 출력 형식을 만든다. 생존표는 고정 코호트로 계산한
값이라 시점에 따라 바뀌지 않는다. 시점에 따라 바뀌는 것은 주변 점포 수이므로,
변화는 개·폐업 집계(`timeline.py`)로 답하고 생존률은 참고로 함께 보여준다.
"""

from __future__ import annotations

import pandas as pd

from src.monitor.timeline import open_count_at, slice_window


def _to_month(value: str) -> str:
    """'2026-09-13' 또는 '2026-09' → '2026-09'."""
    text = str(value).strip()
    if len(text) < 7:
        raise ValueError(f"날짜 형식이 아니다: {value!r}")
    return text[:7]


def _particle(word: str) -> str:
    """받침이 있으면 '이', 없으면 '가'. distribution.py도 쓴다."""
    if not word:
        return "가"
    code = ord(word[-1])
    if 0xAC00 <= code <= 0xD7A3:
        return "이" if (code - 0xAC00) % 28 else "가"
    return "가"


def describe(sgg: str, category: str, opened: int, closed: int, net: int) -> str:
    if opened == 0 and closed == 0:
        return f"{sgg} {category}{_particle(category)} 이 기간에 새로 열거나 닫은 곳이 없다."
    body = f"{sgg} {category}{_particle(category)} 이 기간에 {opened}곳 열고 {closed}곳 닫았다."
    if net > 0:
        return body + f" 경쟁 상대가 {net}곳 늘었다."
    if net < 0:
        return body + f" 경쟁 상대가 {abs(net)}곳 줄었다."
    return body + " 수는 그대로다."


def compare(
    timeline: pd.DataFrame,
    sido: str,
    sgg: str,
    category: str,
    computed_at: str,
    as_of: str,
) -> dict:
    """두 시점 사이의 변화. computed_at은 프로젝트를 만든 날, as_of는 확인하는 날."""
    start = _to_month(computed_at)
    end = _to_month(as_of)
    if end < start:
        return {"error": "as_of_before_computed_at", "reason": "확인 시점이 저장 시점보다 앞선다."}

    window = slice_window(timeline, sido, sgg, category, start, end)
    opened = int(window["opened"].sum())
    closed = int(window["closed"].sum())
    net = opened - closed

    return {
        "from": start,
        "to": end,
        "sido": sido,
        "sgg": sgg,
        "category": category,
        "same_category_opened": opened,
        "same_category_closed": closed,
        "net_change": net,
        "open_count_then": open_count_at(timeline, sido, sgg, category, start),
        "open_count_now": open_count_at(timeline, sido, sgg, category, end),
        "message": describe(sgg, category, opened, closed, net),
    }


def monthly_series(
    timeline: pd.DataFrame, sido: str, sgg: str, category: str, start_month: str, end_month: str
) -> list[dict]:
    """화면 그래프용. 구간 안의 월별 개·폐업."""
    window = slice_window(timeline, sido, sgg, category, _to_month(start_month), _to_month(end_month))
    return [
        {"month": row.month, "opened": int(row.opened), "closed": int(row.closed)}
        for row in window.sort_values("month").itertuples()
    ]
