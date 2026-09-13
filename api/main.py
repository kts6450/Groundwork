"""검증기 HTTP API. src.scoring만 호출한다."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.branding.generate import generate_brand
from src.monitor.changes import compare, monthly_series
from src.scoring.paths import TIMELINE_PARQUET
from src.concept.generate import generate_concept
from src.scoring.catalog import license_choices, nation_rates
from src.scoring.verify import SurvivalTables, load_tables, verify

tables: SurvivalTables | None = None
timeline: pd.DataFrame | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global tables, timeline
    tables = load_tables()
    if TIMELINE_PARQUET.exists():
        timeline = pd.read_parquet(TIMELINE_PARQUET)
    yield


app = FastAPI(title="남음", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class VerifyIn(BaseModel):
    address: str = Field(min_length=1)
    business_type: str = Field(min_length=1)


class ChangesIn(BaseModel):
    """저장된 프로젝트의 위치·업종과 두 시점. 저장소가 없어 값을 직접 받는다."""

    sido: str = Field(min_length=1)
    sgg: str = Field(min_length=1)
    category: str = Field(min_length=1)
    computed_at: str = Field(min_length=7)
    as_of: str = Field(min_length=7)


class ConceptIn(VerifyIn):
    budget_krw: int | None = Field(default=None, ge=0)
    experience: str = Field(default="none")
    preferences: list[str] = Field(default_factory=list)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/catalog")
def catalog() -> dict:
    if tables is None:
        raise HTTPException(503, "tables not loaded")
    return {"business_types": license_choices(), "nation": nation_rates(tables)}


@app.post("/verify")
def post_verify(body: VerifyIn) -> dict:
    if tables is None:
        raise HTTPException(503, "tables not loaded")
    return verify(body.address.strip(), body.business_type.strip(), tables)


@app.post("/changes")
def post_changes(body: ChangesIn) -> dict:
    """5단계. 저장 시점 이후 같은 업종이 몇 곳 열고 닫았는지."""
    if timeline is None:
        raise HTTPException(503, "timeline not built; run python -m src.monitor.run_timeline")
    try:
        result = compare(timeline, body.sido, body.sgg, body.category, body.computed_at, body.as_of)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if "error" not in result:
        result["monthly"] = monthly_series(
            timeline, body.sido, body.sgg, body.category, body.computed_at, body.as_of
        )
    return result


@app.post("/plan")
def post_plan(body: ConceptIn) -> dict:
    """1~3단계를 한 번에. 검증 → 컨셉 → 브랜딩."""
    if tables is None:
        raise HTTPException(503, "tables not loaded")
    verdict = verify(body.address.strip(), body.business_type.strip(), tables)
    concept = generate_concept(
        verdict,
        budget_krw=body.budget_krw,
        experience=body.experience,
        preferences=body.preferences,
    )
    brand = generate_brand(concept, verdict.get("category", "기타"), preferences=body.preferences)
    return {"verdict": verdict, "concept": concept, "brand": brand}


@app.post("/concept")
def post_concept(body: ConceptIn) -> dict:
    """2단계. 검증부터 다시 하고 그 결과를 근거로 컨셉을 만든다."""
    if tables is None:
        raise HTTPException(503, "tables not loaded")
    verdict = verify(body.address.strip(), body.business_type.strip(), tables)
    concept = generate_concept(
        verdict,
        budget_krw=body.budget_krw,
        experience=body.experience,
        preferences=body.preferences,
    )
    return {"verdict": verdict, "concept": concept}
