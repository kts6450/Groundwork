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
from src.monitor.assets import generate_asset
from src.monitor.changes import compare, monthly_series
from src.monitor.distribution import describe as describe_distribution, distribution
from src.projects.store import ProjectError, get_project, list_projects, save_project
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
    """저장된 프로젝트를 project_id로 부르거나, 값을 직접 넘긴다."""

    project_id: str | None = None
    sido: str | None = None
    sgg: str | None = None
    category: str | None = None
    computed_at: str | None = None
    as_of: str = Field(min_length=7)


class SaveProjectIn(VerifyIn):
    user_id: str = Field(min_length=1)
    budget_krw: int | None = Field(default=None, ge=0)
    experience: str = Field(default="none")
    preferences: list[str] = Field(default_factory=list)
    computed_at: str | None = None


class AssetIn(BaseModel):
    project_id: str = Field(min_length=1)
    asset: str = Field(min_length=1)
    context: str = ""


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


@app.post("/projects")
def post_project(body: SaveProjectIn) -> dict:
    """4단계 결과를 저장한다. 검증·컨셉·브랜딩을 한 번에 계산해 한 덩어리로 넣는다."""
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
    try:
        return save_project(
            body.user_id, body.address.strip(), verdict, concept, brand, computed_at=body.computed_at
        )
    except ProjectError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/projects")
def get_projects(user_id: str, limit: int = 20) -> dict:
    return {"projects": list_projects(user_id, limit=limit)}


@app.get("/projects/{project_id}")
def get_one_project(project_id: str) -> dict:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(404, "project not found")
    return project


@app.get("/distribution")
def get_distribution(sido: str, sgg: str) -> dict:
    """이 시군구에 어떤 업종이 몰려 있는지. 전국 구성비 대비 배수."""
    if timeline is None:
        raise HTTPException(503, "timeline not built; run python -m src.monitor.run_timeline")
    result = distribution(timeline, sido.strip(), sgg.strip())
    result["summary"] = describe_distribution(result)
    return result


@app.post("/changes")
def post_changes(body: ChangesIn) -> dict:
    """5단계. 저장 시점 이후 같은 업종이 몇 곳 열고 닫았는지."""
    if timeline is None:
        raise HTTPException(503, "timeline not built; run python -m src.monitor.run_timeline")

    sido, sgg, category, computed_at = body.sido, body.sgg, body.category, body.computed_at
    if body.project_id:
        project = get_project(body.project_id)
        if project is None:
            raise HTTPException(404, "project not found")
        sido = project["location"]["sido"]
        sgg = project["location"]["sgg"]
        category = project["category"]
        computed_at = project["computed_at"]
    if not all([sido, sgg, category, computed_at]):
        raise HTTPException(422, "project_id 또는 sido·sgg·category·computed_at이 필요하다")

    try:
        result = compare(timeline, sido, sgg, category, computed_at, body.as_of)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if "error" not in result:
        result["monthly"] = monthly_series(timeline, sido, sgg, category, computed_at, body.as_of)
    return result


@app.post("/assets")
def post_asset(body: AssetIn) -> dict:
    """7-2. 저장된 브랜드 정체성으로 홍보물을 만든다."""
    project = get_project(body.project_id)
    if project is None:
        raise HTTPException(404, "project not found")
    return generate_asset(project, body.asset, body.context)


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
