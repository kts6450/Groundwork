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

from src.scoring.catalog import license_choices, nation_rates
from src.scoring.verify import SurvivalTables, load_tables, verify

tables: SurvivalTables | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global tables
    tables = load_tables()
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
