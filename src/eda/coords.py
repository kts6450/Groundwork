from __future__ import annotations

import math
import re

from pyproj import Transformer

_TRANSFORMERS: dict[str, Transformer] = {}

CANDIDATE_CRS = (
    "EPSG:5174",
    "EPSG:2097",
    "EPSG:5178",
    "EPSG:5181",
    "EPSG:5186",
)

CITY_CENTROIDS = {
    "서울특별시": (126.9780, 37.5665),
    "부산광역시": (129.0756, 35.1796),
    "대구광역시": (128.6014, 35.8714),
    "인천광역시": (126.7052, 37.4563),
    "광주광역시": (126.8526, 35.1595),
    "대전광역시": (127.3845, 36.3504),
    "울산광역시": (129.3114, 35.5384),
    "세종특별자치시": (127.2892, 36.4800),
    "경기도": (127.0100, 37.2800),
    "강원특별자치도": (128.2100, 37.8200),
    "강원도": (128.2100, 37.8200),
    "충청북도": (127.6500, 36.6300),
    "충청남도": (126.8000, 36.5200),
    "전북특별자치도": (127.1500, 35.8200),
    "전라북도": (127.1500, 35.8200),
    "전라남도": (126.9000, 34.8100),
    "경상북도": (128.7200, 36.2500),
    "경상남도": (128.2500, 35.2300),
    "제주특별자치도": (126.5312, 33.4996),
    "제주도": (126.5312, 33.4996),
}

_SIDO_RE = re.compile(
    r"^(?P<sido>서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|"
    r"대전광역시|울산광역시|세종특별자치시|전남광주통합특별시|경기도|강원특별자치도|강원도|"
    r"충청북도|충청남도|전북특별자치도|전라북도|전라남도|경상북도|경상남도|"
    r"제주특별자치도|제주도)"
    r"(?:\s+(?P<sgg>[가-힣]+시(?:\s+[가-힣]+구)?|[가-힣]+구|[가-힣]+군))?"
)

_GWANGJU_GU = frozenset({"동구", "서구", "남구", "북구", "광산구"})

# 일반구가 있는 시만 시+구를 남긴다. '유구읍'·'행구동'처럼 구로 끝나는 읍·동은 시로 되돌린다.
# 화성 동탄·만세·병점·효행은 인허가 주소에 구 표기가 있어 인정한다.
GENERAL_GU: dict[str, frozenset[str]] = {
    "수원시": frozenset({"장안구", "권선구", "팔달구", "영통구"}),
    "성남시": frozenset({"수정구", "중원구", "분당구"}),
    "안양시": frozenset({"만안구", "동안구"}),
    "안산시": frozenset({"상록구", "단원구"}),
    "고양시": frozenset({"덕양구", "일산동구", "일산서구"}),
    "용인시": frozenset({"처인구", "기흥구", "수지구"}),
    "부천시": frozenset({"원미구", "소사구", "오정구"}),
    "청주시": frozenset({"상당구", "서원구", "흥덕구", "청원구"}),
    "천안시": frozenset({"동남구", "서북구"}),
    "전주시": frozenset({"완산구", "덕진구"}),
    "포항시": frozenset({"남구", "북구"}),
    "창원시": frozenset({"의창구", "성산구", "마산합포구", "마산회원구", "진해구"}),
    "화성시": frozenset({"동탄구", "만세구", "병점구", "효행구"}),
}


def _collapse_false_gu(sgg: str) -> str:
    if "시 " not in sgg:
        return sgg
    city, _, rest = sgg.partition(" ")
    allowed = GENERAL_GU.get(city)
    if allowed is None or rest not in allowed:
        return city
    return sgg


def _normalize_parsed(sido: str, sgg: str) -> tuple[str, str]:
    if sido == "세종특별자치시":
        return (sido, "")
    if sido == "전남광주통합특별시":
        if sgg in _GWANGJU_GU:
            return ("광주광역시", sgg)
        if sgg:
            return ("전라남도", _collapse_false_gu(sgg))
        return ("", "")
    return (sido, _collapse_false_gu(sgg))


def parse_sido_sgg(address: str | None) -> tuple[str, str]:
    if not address or not isinstance(address, str):
        return ("", "")
    match = _SIDO_RE.match(address.strip())
    if not match:
        return ("", "")
    return _normalize_parsed(match.group("sido"), match.group("sgg") or "")


def transform_xy(x: float, y: float, crs: str) -> tuple[float, float]:
    if crs not in _TRANSFORMERS:
        _TRANSFORMERS[crs] = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lon, lat = _TRANSFORMERS[crs].transform(x, y)
    return float(lon), float(lat)


def within_korea(lon: float, lat: float) -> bool:
    return 124.0 <= lon <= 132.0 and 33.0 <= lat <= 39.5


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def score_crs(samples: list[dict], crs: str) -> dict:
    distances: list[float] = []
    in_korea = 0
    converted = 0
    for row in samples:
        try:
            lon, lat = transform_xy(float(row["x"]), float(row["y"]), crs)
        except (TypeError, ValueError):
            continue
        converted += 1
        if within_korea(lon, lat):
            in_korea += 1
        centroid = CITY_CENTROIDS.get(str(row.get("sido") or ""))
        if centroid:
            distances.append(haversine_km(lon, lat, centroid[0], centroid[1]))
    distances.sort()
    median_km = distances[len(distances) // 2] if distances else None
    return {
        "crs": crs,
        "converted": converted,
        "in_korea": in_korea,
        "median_km_to_sido": median_km,
    }


def parse_sido_sgg_series(address: "pd.Series") -> "pd.DataFrame":
    """parse_sido_sgg의 벡터 버전. 컬럼 sido, sgg (실패 시 빈 문자열)."""
    import pandas as pd  # noqa: PLC0415 - eda 모듈은 pyproj만 필수 의존

    text = address.astype("string").str.strip()
    parts = text.str.extract(_SIDO_RE)
    out = pd.DataFrame({"sido": parts["sido"].fillna(""), "sgg": parts["sgg"].fillna("")})
    gwangju = out["sido"].eq("전남광주통합특별시") & out["sgg"].isin(_GWANGJU_GU)
    jeonnam = out["sido"].eq("전남광주통합특별시") & ~out["sgg"].isin(_GWANGJU_GU) & (out["sgg"] != "")
    unknown = out["sido"].eq("전남광주통합특별시") & (out["sgg"] == "")
    out.loc[out["sido"] == "세종특별자치시", "sgg"] = ""
    out.loc[gwangju, "sido"] = "광주광역시"
    out.loc[jeonnam, "sido"] = "전라남도"
    out.loc[unknown, ["sido", "sgg"]] = ""
    has_city_gu = out["sgg"].str.contains("시 ", na=False)
    if has_city_gu.any():
        collapsed = out.loc[has_city_gu, "sgg"].map(_collapse_false_gu)
        out.loc[has_city_gu, "sgg"] = collapsed
    return out
