from src.scoring.categories import (
    CATEGORIES,
    EXCLUDE,
    LICENSE_MAP,
    SANGA_MAP,
    map_license,
    map_sanga,
)


def test_every_mapped_value_points_to_a_known_bucket() -> None:
    allowed = set(CATEGORIES) | {EXCLUDE}
    assert set(LICENSE_MAP.values()) <= allowed
    assert set(SANGA_MAP.values()) <= allowed


def test_map_license_core_buckets() -> None:
    assert map_license("한식") == "한식"
    assert map_license("중국식") == "중식"
    assert map_license("경양식") == "양식"
    assert map_license("호프/통닭") == "치킨·호프"
    assert map_license("정종/대포집/소주방") == "주점"
    assert map_license("커피숍") == "카페"
    assert map_license("다방") == "카페"
    assert map_license("통닭(치킨)") == "치킨·호프"
    assert map_license("식육(숯불구이)") == "고기구이"


def test_map_license_excludes_non_store_and_non_food() -> None:
    assert map_license("편의점") == EXCLUDE
    assert map_license("백화점") == EXCLUDE
    assert map_license("푸드트럭") == EXCLUDE
    assert map_license("출장조리") == EXCLUDE


def test_map_license_unknown_or_blank_is_none() -> None:
    assert map_license("존재하지않는업태") is None
    assert map_license("") is None
    assert map_license(None) is None


def test_map_license_strips_whitespace() -> None:
    assert map_license(" 한식 ") == "한식"


def test_map_sanga_uses_subcategory() -> None:
    assert map_sanga("한식", "백반/한정식") == "한식"
    assert map_sanga("한식", "돼지고기 구이/찜") == "고기구이"
    assert map_sanga("한식", "횟집") == "회·해산물"
    assert map_sanga("비알코올", "카페") == "카페"
    assert map_sanga("기타 간이", "치킨") == "치킨·호프"
    assert map_sanga("기타 간이", "빵/도넛") == "디저트"
    assert map_sanga("주점", "생맥주 전문") == "주점"


def test_map_sanga_excludes_cafeteria_and_unknown_is_none() -> None:
    assert map_sanga("구내식당·뷔페", "구내식당") == EXCLUDE
    assert map_sanga("한식", "없는소분류") is None
