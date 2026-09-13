from pathlib import Path  # noqa: F401  (report writer type hint)

from src.eda.paths import PROJECT_ROOT, REPORTS_DIR

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

SURVIVAL_SGG_PARQUET = DATA_PROCESSED / "survival_sgg_category.parquet"
SURVIVAL_SIDO_PARQUET = DATA_PROCESSED / "survival_sido_category.parquet"
SURVIVAL_NATION_PARQUET = DATA_PROCESSED / "survival_category.parquet"
SURVIVAL_REPORT_MD = REPORTS_DIR / "survival.md"
CATEGORIES_REPORT_MD = REPORTS_DIR / "categories.md"
BACKTEST_REPORT_MD = REPORTS_DIR / "backtest.md"
BACKTEST_SCORED_PARQUET = DATA_PROCESSED / "backtest_scored.parquet"
BACKTEST_EVIDENCE_JSON = DATA_PROCESSED / "backtest_evidence.json"
TIMELINE_PARQUET = DATA_PROCESSED / "timeline_sgg_category.parquet"
