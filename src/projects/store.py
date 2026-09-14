"""사용자 프로젝트 저장 (인터페이스 6번).

4단계 결과를 한 덩어리로 저장하고, 5단계가 그걸 읽어 새 시점으로 다시 계산한다.

지금은 SQLite 한 파일이다. Supabase(PostgreSQL)로 갈아끼울 때 이 모듈의 함수 시그니처만
지키면 바깥 코드는 바뀌지 않는다. `user_id`는 로그인이 없어 지금은 호출자가 넘기는 문자열이고,
Supabase를 붙이면 인증된 사용자 id가 들어온다.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from src.scoring.paths import DATA_PROCESSED

DB_PATH = DATA_PROCESSED / "projects.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id   TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    computed_at  TEXT NOT NULL,
    sido         TEXT NOT NULL,
    sgg          TEXT NOT NULL,
    address      TEXT NOT NULL,
    category     TEXT NOT NULL,
    business_type TEXT NOT NULL,
    payload      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id, created_at DESC);
"""


class ProjectError(ValueError):
    """저장할 수 없거나 찾을 수 없을 때."""


@contextmanager
def connect(db_path: Path | None = None):
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row_to_project(row: sqlite3.Row) -> dict:
    payload = json.loads(row["payload"])
    return {
        "project_id": row["project_id"],
        "user_id": row["user_id"],
        "created_at": row["created_at"],
        "computed_at": row["computed_at"],
        "location": {"address": row["address"], "sido": row["sido"], "sgg": row["sgg"]},
        "category": row["category"],
        "business_type": row["business_type"],
        "verdict": payload.get("verdict", {}),
        "concept": payload.get("concept", {}),
        "brand": payload.get("brand", {}),
    }


def save_project(
    user_id: str,
    address: str,
    verdict: dict,
    concept: dict | None = None,
    brand: dict | None = None,
    computed_at: str | None = None,
    db_path: Path | None = None,
) -> dict:
    """4단계 결과를 저장하고 저장된 프로젝트를 돌려준다."""
    if verdict.get("error"):
        raise ProjectError("검증에 실패한 결과는 저장하지 않는다")
    if not verdict.get("sido") or not verdict.get("sgg"):
        raise ProjectError("시도·시군구를 읽지 못한 결과는 저장하지 않는다")
    if not user_id:
        raise ProjectError("user_id가 없다")

    today = date.today().isoformat()
    project_id = str(uuid.uuid4())
    payload = {"verdict": verdict, "concept": concept or {}, "brand": brand or {}}

    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO projects (project_id, user_id, created_at, computed_at, sido, sgg,"
            " address, category, business_type, payload) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                project_id,
                user_id,
                today,
                computed_at or today,
                verdict["sido"],
                verdict["sgg"],
                address,
                verdict.get("category", ""),
                verdict.get("business_type", ""),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        row = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
    return _row_to_project(row)


def get_project(project_id: str, db_path: Path | None = None) -> dict | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
    return _row_to_project(row) if row else None


def list_projects(user_id: str, limit: int = 20, db_path: Path | None = None) -> list[dict]:
    """목록 화면용. 큰 payload는 빼고 요약만 준다."""
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT project_id, created_at, computed_at, sido, sgg, address, category, business_type"
            " FROM projects WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_project(project_id: str, db_path: Path | None = None) -> bool:
    with connect(db_path) as conn:
        cursor = conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
        return cursor.rowcount > 0
