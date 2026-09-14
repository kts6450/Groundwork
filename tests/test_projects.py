import pytest

from src.projects.store import (
    ProjectError,
    delete_project,
    get_project,
    list_projects,
    save_project,
)

VERDICT = {
    "sido": "서울특별시",
    "sgg": "마포구",
    "business_type": "커피숍",
    "category": "카페",
    "level": "시군구",
    "n": 1499,
    "surv_3y": 0.571,
    "nation_3y": 0.646,
    "grade": "위험",
}
CONCEPT = {"source": "mock", "concept": {"one_liner": "조용한 로스터리"}, "menu": [], "grounds": []}
BRAND = {"source": "mock", "names": [{"name": "머무름", "reason": "…", "risk": "…"}]}


@pytest.fixture()
def db(tmp_path):
    return tmp_path / "projects.sqlite3"


def test_save_returns_the_stored_project(db) -> None:
    saved = save_project("user-1", "서울특별시 마포구 양화로 100", VERDICT, CONCEPT, BRAND, db_path=db)

    assert saved["project_id"]
    assert saved["location"]["sgg"] == "마포구"
    assert saved["category"] == "카페"
    assert saved["concept"]["concept"]["one_liner"] == "조용한 로스터리"


def test_saved_project_can_be_read_back(db) -> None:
    saved = save_project("user-1", "주소", VERDICT, CONCEPT, BRAND, db_path=db)

    loaded = get_project(saved["project_id"], db_path=db)

    assert loaded == saved


def test_get_returns_none_for_unknown_id(db) -> None:
    assert get_project("no-such-id", db_path=db) is None


def test_computed_at_defaults_to_today_and_can_be_overridden(db) -> None:
    default = save_project("user-1", "주소", VERDICT, db_path=db)
    pinned = save_project("user-1", "주소", VERDICT, computed_at="2024-03-01", db_path=db)

    assert default["computed_at"] == default["created_at"]
    assert pinned["computed_at"] == "2024-03-01"


def test_projects_are_listed_newest_first_and_scoped_to_the_user(db) -> None:
    save_project("user-1", "첫 번째", VERDICT, db_path=db)
    save_project("user-1", "두 번째", VERDICT, db_path=db)
    save_project("user-2", "남의 것", VERDICT, db_path=db)

    rows = list_projects("user-1", db_path=db)

    assert [r["address"] for r in rows] == ["두 번째", "첫 번째"]
    assert all(r["address"] != "남의 것" for r in rows)


def test_list_respects_the_limit(db) -> None:
    for i in range(5):
        save_project("user-1", f"주소 {i}", VERDICT, db_path=db)

    assert len(list_projects("user-1", limit=2, db_path=db)) == 2


def test_list_omits_the_bulky_payload(db) -> None:
    save_project("user-1", "주소", VERDICT, CONCEPT, BRAND, db_path=db)

    row = list_projects("user-1", db_path=db)[0]

    assert "verdict" not in row
    assert "concept" not in row
    assert row["category"] == "카페"


def test_delete_removes_the_project(db) -> None:
    saved = save_project("user-1", "주소", VERDICT, db_path=db)

    assert delete_project(saved["project_id"], db_path=db) is True
    assert get_project(saved["project_id"], db_path=db) is None
    assert delete_project(saved["project_id"], db_path=db) is False


def test_failed_verdicts_are_not_saved(db) -> None:
    with pytest.raises(ProjectError, match="검증에 실패"):
        save_project("user-1", "주소", {"error": "excluded"}, db_path=db)


def test_verdict_without_a_region_is_not_saved(db) -> None:
    with pytest.raises(ProjectError, match="시도"):
        save_project("user-1", "주소", {**VERDICT, "sgg": ""}, db_path=db)


def test_user_id_is_required(db) -> None:
    with pytest.raises(ProjectError, match="user_id"):
        save_project("", "주소", VERDICT, db_path=db)


def test_concept_and_brand_are_optional(db) -> None:
    saved = save_project("user-1", "주소", VERDICT, db_path=db)

    assert saved["concept"] == {}
    assert saved["brand"] == {}
