from __future__ import annotations

import json
import sys
from pathlib import Path

from src.eda.convert import run as convert_run
from src.eda.analyze import run as analyze_run
from src.eda.paths import PROFILE_JSON, REPORT_MD
from src.eda.report import write as write_report


def main(force: bool = True) -> Path:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("1/3 convert raw -> parquet")
    convert_run(force=force)
    print("2/3 analyze")
    result = analyze_run()
    print("3/3 write report")
    write_report(result)
    summary = {
        "report": str(REPORT_MD),
        "profile": str(PROFILE_JSON),
        "best_crs": {name: block["best_crs"] for name, block in result["coords"].items()},
        "admin_join_direct": result["keys"]["admin_join"]["direct_join"],
        "admin_join_first8": result["keys"]["admin_join"]["join_on_pop_first8"],
        "time_filter": {
            name: block["usable_for_asof"] for name, block in result["time_filter"].items()
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return REPORT_MD


if __name__ == "__main__":
    main(force="--no-force" not in sys.argv)
