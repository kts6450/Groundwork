"""시군구 × 업종 × 연월 개·폐업 집계표 생성.

실행: python -m src.monitor.run_timeline
출력: data/processed/timeline_sgg_category.parquet
"""

from __future__ import annotations

from src.monitor.timeline import build_timeline
from src.scoring import paths
from src.scoring.run_survival import load_license, prepare


def main() -> None:
    paths.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    timeline = build_timeline(prepare(load_license()))
    timeline.to_parquet(paths.TIMELINE_PARQUET, index=False)

    months = timeline["month"]
    areas = timeline[["sido", "sgg"]].drop_duplicates()
    print(f"rows={len(timeline):,} 시군구={len(areas):,} 업종={timeline['category'].nunique()}")
    print(f"기간 {months.min()} ~ {months.max()}")
    print(f"wrote {paths.TIMELINE_PARQUET.name}")


if __name__ == "__main__":
    main()
