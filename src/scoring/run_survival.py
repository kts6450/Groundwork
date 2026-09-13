"""2주 차: 업종 매핑 → 코호트 → 시군구 × 업종 생존표.

실행: python -m src.scoring.run_survival
입력: data/interim/*.parquet (EDA convert 산출물)
출력: data/processed/survival_*.parquet, reports/survival.md, reports/categories.md
"""

from __future__ import annotations

import pandas as pd

from src.eda.coords import parse_sido_sgg_series
from src.eda.history import parse_license_date
from src.eda.paths import LICENSE_GENERAL_PARQUET, LICENSE_REST_PARQUET, SANGA_FOOD_PARQUET
from src.scoring import paths
from src.scoring.audit import categories_at_risk, retired_types, usage_by_type
from src.scoring.categories import EXCLUDE, map_license, map_sanga
from src.scoring.report_survival import write_categories_report, write_survival_report
from src.scoring.survival import CohortSpec, build_cohort, normalize_sido, survival_table

SPEC = CohortSpec(
    opened_from=pd.Timestamp("2015-01-01"),
    opened_to=pd.Timestamp("2023-06-30"),
    data_cutoff=pd.Timestamp("2026-09-09"),
)
MIN_N = 10
LICENSE_COLS = ["인허가일자", "폐업일자", "영업상태명", "업태구분명", "도로명주소", "지번주소"]


def load_license() -> pd.DataFrame:
    frames = []
    for source, path in (("일반음식점", LICENSE_GENERAL_PARQUET), ("휴게음식점", LICENSE_REST_PARQUET)):
        df = pd.read_parquet(path, columns=LICENSE_COLS)
        df["source"] = source
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def prepare(raw: pd.DataFrame) -> pd.DataFrame:
    address = raw["도로명주소"].astype("string")
    address = address.where(address.notna() & (address.str.strip() != ""), raw["지번주소"].astype("string"))
    region = parse_sido_sgg_series(address)
    region["sido"] = region["sido"].map(normalize_sido)
    region.loc[(region["sido"] == "세종특별자치시"), "sgg"] = "세종특별자치시"

    business = raw["업태구분명"].astype("string").str.strip()
    return pd.DataFrame(
        {
            "source": raw["source"],
            "business_type": business,
            "category": business.map(map_license).astype("object"),
            "permit": parse_license_date(raw["인허가일자"]),
            "closed": parse_license_date(raw["폐업일자"]),
            "status": raw["영업상태명"],
            "sido": region["sido"].astype("object"),
            "sgg": region["sgg"].astype("object"),
        }
    )


def category_coverage(prepared: pd.DataFrame) -> dict:
    counts = prepared.groupby(["source", "business_type"], dropna=False).size().reset_index(name="n")
    counts["category"] = counts["business_type"].map(map_license)
    unmapped = counts[counts["category"].isna()].sort_values("n", ascending=False)
    excluded = counts[counts["category"] == EXCLUDE].sort_values("n", ascending=False)
    return {"counts": counts, "unmapped": unmapped, "excluded": excluded}


def sanga_coverage() -> pd.DataFrame:
    sanga = pd.read_parquet(SANGA_FOOD_PARQUET, columns=["상권업종중분류명", "상권업종소분류명"])
    counts = sanga.groupby(["상권업종중분류명", "상권업종소분류명"]).size().reset_index(name="n")
    counts["category"] = [
        map_sanga(mid, sub) for mid, sub in zip(counts["상권업종중분류명"], counts["상권업종소분류명"])
    ]
    return counts.sort_values("n", ascending=False)


def main() -> None:
    paths.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    raw = load_license()
    prepared = prepare(raw)
    coverage = category_coverage(prepared)
    sanga_counts = sanga_coverage()

    mapped = prepared[prepared["category"].notna() & (prepared["category"] != EXCLUDE)]
    usage = usage_by_type(mapped, SPEC.opened_from, SPEC.opened_to)
    retired = retired_types(usage)
    at_risk = categories_at_risk(usage)

    cohort, dropped = build_cohort(prepared, SPEC)
    no_region = cohort["sido"] == ""
    dropped["region_unparsed"] = int(no_region.sum())
    cohort_region = cohort[~no_region]

    nation, _ = survival_table(cohort, by=["category"], min_n=MIN_N)
    sido, sido_small = survival_table(cohort_region, by=["sido", "category"], min_n=MIN_N)
    sgg, sgg_small = survival_table(cohort_region, by=["sido", "sgg", "category"], min_n=MIN_N)

    nation.to_parquet(paths.SURVIVAL_NATION_PARQUET, index=False)
    sido.to_parquet(paths.SURVIVAL_SIDO_PARQUET, index=False)
    sgg.to_parquet(paths.SURVIVAL_SGG_PARQUET, index=False)

    write_categories_report(paths.CATEGORIES_REPORT_MD, coverage, sanga_counts, usage=usage, retired=retired, at_risk=at_risk)
    write_survival_report(
        paths.SURVIVAL_REPORT_MD,
        spec=SPEC,
        min_n=MIN_N,
        total_rows=len(prepared),
        dropped=dropped,
        cohort=cohort,
        nation=nation,
        sido=sido,
        sgg=sgg,
        sido_small=sido_small,
        sgg_small=sgg_small,
        retired=retired,
        at_risk=at_risk,
    )
    print(f"cohort={len(cohort):,} nation={len(nation)} sido={len(sido)} sgg={len(sgg)} (sgg n<{MIN_N}: {sgg_small})")
    if retired:
        print("폐지된 업태: " + ", ".join(f"{r.business_type}(최근 {r.recent})" for r in retired))
    if at_risk:
        print("영향받는 묶음: " + ", ".join(f"{c} {share:.0%}" for c, share in sorted(at_risk.items(), key=lambda kv: -kv[1])))
    print(f"wrote {paths.SURVIVAL_REPORT_MD.name}, {paths.CATEGORIES_REPORT_MD.name}")


if __name__ == "__main__":
    main()
