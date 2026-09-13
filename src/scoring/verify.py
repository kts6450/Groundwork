"""주소·업태 → 시군구×업종 생존률과 합격/주의/위험.

시군구 표에 없으면 시도, 그것도 없으면 전국으로 내려간다.
등급: 해당 칸 3년 생존 − 전국 같은 업종 3년 생존. +5%p 합격, −5%p 위험, 사이는 주의.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.eda.coords import parse_sido_sgg
from src.scoring.categories import EXCLUDE, map_license
from src.scoring.paths import SURVIVAL_NATION_PARQUET, SURVIVAL_SGG_PARQUET, SURVIVAL_SIDO_PARQUET
from src.scoring.survival import normalize_sido

THRESHOLD = 0.05


@dataclass(frozen=True)
class SurvivalTables:
    nation: pd.DataFrame
    sido: pd.DataFrame
    sgg: pd.DataFrame


def load_tables() -> SurvivalTables:
    return SurvivalTables(
        nation=pd.read_parquet(SURVIVAL_NATION_PARQUET),
        sido=pd.read_parquet(SURVIVAL_SIDO_PARQUET),
        sgg=pd.read_parquet(SURVIVAL_SGG_PARQUET),
    )


def grade(local_3y: float, nation_3y: float, threshold: float = THRESHOLD) -> str:
    diff = round(local_3y - nation_3y, 6)
    if diff >= threshold:
        return "합격"
    if diff <= -threshold:
        return "위험"
    return "주의"


def verify(address: str, business_type: str, tables: SurvivalTables) -> dict:
    category = map_license(business_type)
    if category is None:
        payload = {"error": "unmapped", "business_type": business_type}
        from src.scoring.catalog import explain

        payload["reason"] = explain(payload)
        return payload
    if category == EXCLUDE:
        payload = {"error": "excluded", "business_type": business_type, "category": category}
        from src.scoring.catalog import explain

        payload["reason"] = explain(payload)
        return payload

    sido, sgg = parse_sido_sgg(address)
    sido = normalize_sido(sido)
    if sido == "세종특별자치시":
        sgg = "세종특별자치시"

    nation_row = _lookup(tables.nation, category=category)
    if nation_row is None:
        return {"error": "no_national_rate", "category": category}

    sgg_row = _lookup(tables.sgg, sido=sido, sgg=sgg, category=category) if sido and sgg else None
    sido_row = _lookup(tables.sido, sido=sido, category=category) if sido else None

    if sgg_row is not None:
        level, row = "시군구", sgg_row
    elif sido_row is not None:
        level, row = "시도", sido_row
    else:
        level, row = "전국", nation_row

    local_3y = float(row["surv_3y"])
    nation_3y = float(nation_row["surv_3y"])
    payload = {
        "sido": sido,
        "sgg": sgg,
        "business_type": business_type,
        "category": category,
        "level": level,
        "n": int(row["n"]),
        "surv_1y": float(row["surv_1y"]),
        "surv_3y": local_3y,
        "nation_3y": nation_3y,
        "diff_3y": local_3y - nation_3y,
        "grade": grade(local_3y, nation_3y),
    }
    from src.scoring.catalog import explain

    payload["reason"] = explain(payload)
    return payload


def _lookup(table: pd.DataFrame, **equals: str) -> pd.Series | None:
    mask = pd.Series(True, index=table.index)
    for col, value in equals.items():
        mask &= table[col] == value
    hit = table.loc[mask]
    if hit.empty:
        return None
    return hit.iloc[0]


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 3:
        raise SystemExit('사용: python -m src.scoring.verify "주소" "업태"')
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(verify(sys.argv[1], sys.argv[2], load_tables()), ensure_ascii=False, indent=2))
