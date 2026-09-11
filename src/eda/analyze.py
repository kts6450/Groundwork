from __future__ import annotations

import json

import pandas as pd

from src.eda.coords import CANDIDATE_CRS, parse_sido_sgg, score_crs, transform_xy, within_korea
from src.eda.history import open_at, parse_license_date
from src.eda.io import missing_mask, missing_rate
from src.eda.keys import admin_code_join, code_digit_lengths
from src.eda.paths import (
    LICENSE_GENERAL_PARQUET,
    LICENSE_REST_PARQUET,
    POPULATION_PARQUET,
    PROFILE_JSON,
    SANGA_FOOD_PARQUET,
)

COMPARE_AREAS = [
    ("서울특별시", "종로구"),
    ("서울특별시", "강남구"),
    ("부산광역시", "해운대구"),
    ("세종특별자치시", ""),
]


def run() -> dict:
    profile = json.loads(PROFILE_JSON.read_text(encoding="utf-8"))
    general = pd.read_parquet(LICENSE_GENERAL_PARQUET)
    rest = pd.read_parquet(LICENSE_REST_PARQUET)
    sanga = pd.read_parquet(SANGA_FOOD_PARQUET)
    population = pd.read_parquet(POPULATION_PARQUET)

    licenses = {
        "식품_일반음식점": general,
        "식품_휴게음식점": rest,
    }
    return {
        "profile": profile,
        "categories": _categories(sanga, licenses),
        "keys": _keys(sanga, population, licenses),
        "history": {name: _history(df) for name, df in licenses.items()},
        "coords": {name: _coords(df) for name, df in licenses.items()},
        "coverage": _coverage(sanga, licenses),
        "costs": {name: _costs(df) for name, df in licenses.items()},
        "time_filter": {name: _time_filter(df) for name, df in licenses.items()},
        "buildings": _buildings(sanga),
    }


def _categories(sanga: pd.DataFrame, licenses: dict[str, pd.DataFrame]) -> dict:
    mid = _value_counts(sanga["상권업종중분류명"])
    small = _value_counts(sanga["상권업종소분류명"])
    license_cats = {}
    for name, df in licenses.items():
        license_cats[name] = {
            "업태구분명": _value_counts(df["업태구분명"]),
            "위생업태명": _value_counts(df["위생업태명"]),
        }
    return {
        "sanga_food_rows": int(len(sanga)),
        "sanga_mid": mid,
        "sanga_small_top": small[:40],
        "sanga_small_unique": len(small),
        "license": license_cats,
        "mapping_notes": _mapping_notes(mid, license_cats),
    }


def _keys(sanga: pd.DataFrame, population: pd.DataFrame, licenses: dict[str, pd.DataFrame]) -> dict:
    join = admin_code_join(sanga["행정동코드"], population["행정기관코드"])
    result = {
        "sanga": {
            "행정동코드": _code_field(sanga["행정동코드"]),
            "법정동코드": _code_field(sanga["법정동코드"]),
            "시군구코드": _code_field(sanga["시군구코드"]),
            "도로명주소_missing": missing_rate(sanga["도로명주소"]),
            "지번주소_missing": missing_rate(sanga["지번주소"]),
            "경도_missing": missing_rate(sanga["경도"]),
            "위도_missing": missing_rate(sanga["위도"]),
            "행정동코드_sample": _samples(sanga["행정동코드"]),
            "법정동코드_sample": _samples(sanga["법정동코드"]),
        },
        "population": {
            "행정기관코드": _code_field(population["행정기관코드"]),
            "행정기관코드_sample": _samples(population["행정기관코드"]),
            "rows": int(len(population)),
        },
        "admin_join": join,
        "license": {},
    }
    for name, df in licenses.items():
        addr = df["도로명주소"].astype("string").fillna(df["지번주소"].astype("string"))
        result["license"][name] = {
            "개방자치단체코드": _code_field(df["개방자치단체코드"]),
            "개방자치단체코드_sample": _samples(df["개방자치단체코드"]),
            "도로명주소_missing": missing_rate(df["도로명주소"]),
            "지번주소_missing": missing_rate(df["지번주소"]),
            "좌표X_missing": missing_rate(df["좌표정보(X)"]),
            "좌표Y_missing": missing_rate(df["좌표정보(Y)"]),
            "has_행정동코드": "행정동코드" in df.columns,
            "sido_parse_rate": float(addr.map(lambda v: parse_sido_sgg(v)[0] != "").mean()),
        }
    return result


def _history(df: pd.DataFrame) -> dict:
    permit = parse_license_date(df["인허가일자"])
    closed = parse_license_date(df["폐업일자"])
    status = df["영업상태명"].astype("string").str.strip()
    detail = df["상세영업상태명"].astype("string").str.strip()
    open_years = permit.dt.year.value_counts(dropna=True).sort_index()
    close_years = closed.dt.year.value_counts(dropna=True).sort_index()
    years = sorted(set(open_years.index.astype(int)) | set(close_years.index.astype(int)))
    yearly = [
        {
            "year": int(year),
            "opened": int(open_years.get(year, 0)),
            "closed": int(close_years.get(year, 0)),
        }
        for year in years
        if year >= 1980
    ]
    return {
        "permit_min": _date_str(permit.min()),
        "permit_max": _date_str(permit.max()),
        "closed_min": _date_str(closed.min()),
        "closed_max": _date_str(closed.max()),
        "permit_unparsed": int(permit.isna().sum()),
        "closed_unparsed_among_present": int(
            (~missing_mask(df["폐업일자"]) & closed.isna()).sum()
        ),
        "status": _value_counts(status),
        "detail_status": _value_counts(detail),
        "close_date_missing": missing_rate(df["폐업일자"]),
        "yearly": yearly,
    }


def _coords(df: pd.DataFrame) -> dict:
    x = pd.to_numeric(df["좌표정보(X)"], errors="coerce")
    y = pd.to_numeric(df["좌표정보(Y)"], errors="coerce")
    valid = x.notna() & y.notna()
    addr = df["도로명주소"].astype("string").fillna(df["지번주소"].astype("string"))
    samples = _coord_samples(df, x, y, addr, valid)
    scores = [score_crs(samples, crs) for crs in CANDIDATE_CRS]
    scores = sorted(
        scores,
        key=lambda item: (
            -(item["in_korea"] or 0),
            item["median_km_to_sido"] if item["median_km_to_sido"] is not None else 10**9,
        ),
    )
    best = scores[0]["crs"] if scores else None
    preview = []
    if best:
        for row in samples[:10]:
            lon, lat = transform_xy(row["x"], row["y"], best)
            preview.append(
                {
                    **row,
                    "lon": lon,
                    "lat": lat,
                    "in_korea": within_korea(lon, lat),
                }
            )
    return {
        "n": int(len(df)),
        "xy_missing": float((~valid).mean()),
        "x_min": _opt_float(x.min()),
        "x_max": _opt_float(x.max()),
        "y_min": _opt_float(y.min()),
        "y_max": _opt_float(y.max()),
        "scores": scores,
        "best_crs": best,
        "samples": preview,
    }


def _coverage(sanga: pd.DataFrame, licenses: dict[str, pd.DataFrame]) -> dict:
    sanga_key = (
        sanga["시도명"].astype("string").str.strip()
        + "|"
        + sanga["시군구명"].astype("string").str.strip().fillna("")
    )
    sanga_key = _normalize_area_key(sanga_key)
    sanga_counts = sanga_key.value_counts()

    license_areas: dict[str, tuple[pd.Series, pd.Series]] = {}
    for name, df in licenses.items():
        addr = df["도로명주소"].astype("string").fillna(df["지번주소"].astype("string"))
        keys = addr.map(parse_sido_sgg).map(lambda pair: _area_key(pair[0], pair[1]))
        is_open = ~df["영업상태명"].astype("string").str.contains("폐업", na=False)
        license_areas[name] = (keys, is_open)

    areas = []
    for sido, sgg in COMPARE_AREAS:
        key = _area_key(sido, sgg)
        row = {"sido": sido, "sgg": sgg, "sanga_food": int(sanga_counts.get(key, 0))}
        for name, (keys, is_open) in license_areas.items():
            match = keys == key
            row[f"{name}_all"] = int(match.sum())
            row[f"{name}_open"] = int((match & is_open).sum())
        areas.append(row)
    return {
        "areas": areas,
        "sanga_food_total": int(len(sanga)),
        "license_open_total": {
            name: int((~df["영업상태명"].astype("string").str.contains("폐업", na=False)).sum())
            for name, df in licenses.items()
        },
    }


def _costs(df: pd.DataFrame) -> dict:
    return {
        "월세액": _numeric_field(df["월세액"]),
        "보증액": _numeric_field(df["보증액"]),
        "소재지면적": _numeric_field(df["소재지면적"]),
    }


def _time_filter(df: pd.DataFrame) -> dict:
    permit = parse_license_date(df["인허가일자"])
    closed = parse_license_date(df["폐업일자"])
    status = df["영업상태명"].astype("string")
    is_closed = status.str.contains("폐업", na=False)
    as_of = pd.Timestamp("2022-01-01")
    return {
        "permit_format": "YYYY-MM-DD (숫자 8자리도 허용)",
        "permit_missing": missing_rate(df["인허가일자"]),
        "closed_missing": missing_rate(df["폐업일자"]),
        "closed_status": int(is_closed.sum()),
        "closed_status_without_date": int((is_closed & closed.isna()).sum()),
        "open_status_with_date": int((~is_closed & closed.notna()).sum()),
        "permit_missing_count": int(permit.isna().sum()),
        "open_on_2022_01_01": int(open_at(permit, closed, as_of).sum()),
        "usable_for_asof": bool((permit.notna().mean() > 0.95) and ((is_closed & closed.isna()).mean() < 0.05)),
    }


def _buildings(sanga: pd.DataFrame) -> dict:
    missing = missing_rate(sanga["건물관리번호"])
    valid = sanga.loc[~missing_mask(sanga["건물관리번호"])]
    counts = valid.groupby("건물관리번호").size()
    return {
        "missing_rate": missing,
        "buildings": int(counts.size),
        "stores_with_id": int(len(valid)),
        "min": int(counts.min()) if len(counts) else 0,
        "p50": float(counts.quantile(0.50)) if len(counts) else 0,
        "p90": float(counts.quantile(0.90)) if len(counts) else 0,
        "p99": float(counts.quantile(0.99)) if len(counts) else 0,
        "max": int(counts.max()) if len(counts) else 0,
        "buildings_ge2": int((counts >= 2).sum()) if len(counts) else 0,
        "buildings_ge5": int((counts >= 5).sum()) if len(counts) else 0,
    }


def _coord_samples(df: pd.DataFrame, x: pd.Series, y: pd.Series, addr: pd.Series, valid: pd.Series) -> list[dict]:
    usable = df.loc[valid & ~missing_mask(addr), ["사업장명"]].copy()
    usable["x"] = x[valid]
    usable["y"] = y[valid]
    usable["address"] = addr[valid]
    usable["sido"] = usable["address"].map(lambda v: parse_sido_sgg(v)[0])
    usable = usable[usable["sido"] != ""]
    picked = []
    seen = set()
    for sido, group in usable.groupby("sido"):
        row = group.iloc[0]
        picked.append(
            {
                "name": str(row["사업장명"]),
                "address": str(row["address"]),
                "sido": str(sido),
                "x": float(row["x"]),
                "y": float(row["y"]),
            }
        )
        seen.add(sido)
        if len(picked) >= 10:
            break
    if len(picked) < 10:
        extra = usable.loc[~usable["sido"].isin(seen)].head(10 - len(picked))
        for _, row in extra.iterrows():
            picked.append(
                {
                    "name": str(row["사업장명"]),
                    "address": str(row["address"]),
                    "sido": str(row["sido"]),
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                }
            )
    return picked


def _code_field(series: pd.Series) -> dict:
    stats = code_digit_lengths(series)
    samples = _samples(series)
    return {
        "missing_rate": missing_rate(series),
        "lengths": {str(k): v for k, v in stats.items()},
        "sample": samples,
    }


def _numeric_field(series: pd.Series) -> dict:
    raw_missing = missing_rate(series)
    num = pd.to_numeric(series, errors="coerce")
    zero = int((num == 0).sum())
    positive = num[num > 0]
    return {
        "raw_missing": raw_missing,
        "unparsed": max(0, int(num.isna().sum() - int(missing_mask(series).sum()))),
        "zero": zero,
        "positive_n": int(len(positive)),
        "usable_rate": float(len(positive) / len(series)) if len(series) else 0.0,
        "min": _opt_float(positive.min()) if len(positive) else None,
        "p50": float(positive.median()) if len(positive) else None,
        "p90": float(positive.quantile(0.90)) if len(positive) else None,
        "max": _opt_float(positive.max()) if len(positive) else None,
    }


def _value_counts(series: pd.Series) -> list[dict]:
    text = series.astype("string").str.strip()
    text = text.mask(missing_mask(text))
    counts = text.value_counts(dropna=False)
    rows = []
    for value, count in counts.items():
        label = "NA" if pd.isna(value) else str(value)
        rows.append({"value": label, "n": int(count)})
    return rows


def _samples(series: pd.Series, n: int = 5) -> list[str]:
    text = series.astype("string").str.strip()
    text = text[~missing_mask(text)]
    return [str(v) for v in text.drop_duplicates().head(n).tolist()]


def _mapping_notes(sanga_mid: list[dict], license_cats: dict) -> list[str]:
    mid_names = {row["value"] for row in sanga_mid}
    notes = []
    if any("호프" in name or "주점" in name for name in mid_names):
        notes.append("상가정보는 주점을 음식 대분류 안에 두지만, 인허가는 일반음식점 업태(호프/통닭 등)로 흩어져 있다.")
    rest_values = {row["value"] for row in license_cats.get("식품_휴게음식점", {}).get("업태구분명", [])}
    if "커피숍" in rest_values or "까페" in rest_values:
        notes.append("카페는 휴게음식점 업태(커피숍 등)와 상가 중분류 비알코올/카페가 따로 있어 매핑표가 필요하다.")
    if "편의점" in rest_values or "백화점" in rest_values:
        notes.append("휴게음식점에 편의점·백화점이 들어 있다. 카페 생존률에 넣으면 안 된다.")
    notes.append("인허가 '기타', '패스트푸드', '식육(숯불구이)' 등은 상가 중·소분류와 1:1이 아니다.")
    return notes


def _normalize_area_key(keys: pd.Series) -> pd.Series:
    keys = keys.astype("string")
    return keys.mask(keys.str.startswith("세종특별자치시"), "세종특별자치시|")


def _area_key(sido: str, sgg: str) -> str:
    if sido == "세종특별자치시":
        return "세종특별자치시|"
    return f"{sido}|{sgg}"


def _date_str(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _opt_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
