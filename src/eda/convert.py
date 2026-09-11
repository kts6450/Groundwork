from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.eda.io import detect_encoding, iter_csv_chunks, missing_mask, read_csv_header
from src.eda.paths import (
    DATA_INTERIM,
    LICENSE_COLS,
    LICENSE_GENERAL_CSV,
    LICENSE_GENERAL_PARQUET,
    LICENSE_REST_CSV,
    LICENSE_REST_PARQUET,
    POP_COLS,
    POPULATION_CSV,
    POPULATION_PARQUET,
    PROFILE_JSON,
    SANGA_COLS,
    SANGA_DIR,
    SANGA_FOOD_PARQUET,
)


def run(force: bool = False) -> dict:
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    if not force:
        cached = _load_complete_profile()
        if cached is not None:
            return cached
    profile = {"files": []}

    profile["files"].append(
        _convert_license(LICENSE_GENERAL_CSV, LICENSE_GENERAL_PARQUET, force)
    )
    profile["files"].append(
        _convert_license(LICENSE_REST_CSV, LICENSE_REST_PARQUET, force)
    )
    profile["files"].append(_convert_population(force))
    profile["sanga"] = _convert_sanga(force)

    PROFILE_JSON.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return profile


def _convert_license(src: Path, dest: Path, force: bool) -> dict:
    info = _profile_and_write(
        src,
        dest,
        keep_cols=LICENSE_COLS,
        force=force,
    )
    return info


def _convert_population(force: bool) -> dict:
    return _profile_and_write(
        POPULATION_CSV,
        POPULATION_PARQUET,
        keep_cols=POP_COLS,
        force=force,
    )


def _convert_sanga(force: bool) -> dict:
    csv_files = sorted(p for p in SANGA_DIR.glob("*.csv") if p.is_file())
    per_file = []
    writer = None
    food_rows = 0
    combined_nulls: pd.Series | None = None
    combined_rows = 0
    columns: list[str] = []
    encoding = None
    sample_dtypes: dict[str, str] = {}

    if SANGA_FOOD_PARQUET.exists() and not force:
        cached = _cached_sanga_meta(csv_files)
        if cached is not None:
            return cached

    try:
        for csv_path in csv_files:
            enc = detect_encoding(csv_path)
            encoding = encoding or enc
            header = read_csv_header(csv_path, enc)
            if not columns:
                columns = header
            sample = pd.read_csv(csv_path, encoding=enc, nrows=2000, low_memory=False)
            if not sample_dtypes:
                sample_dtypes = {col: str(sample[col].dtype) for col in sample.columns}

            file_rows = 0
            file_nulls: pd.Series | None = None
            keep = [col for col in SANGA_COLS if col in header]
            for chunk in iter_csv_chunks(csv_path, encoding=enc, chunksize=80_000):
                miss = chunk.apply(missing_mask).sum()
                file_nulls = miss if file_nulls is None else file_nulls.add(miss, fill_value=0)
                file_rows += len(chunk)
                food = chunk.loc[chunk["상권업종대분류명"].astype("string").str.strip() == "음식", keep]
                if food.empty:
                    continue
                table = pa.Table.from_pandas(food, preserve_index=False)
                if writer is None:
                    if SANGA_FOOD_PARQUET.exists():
                        SANGA_FOOD_PARQUET.unlink()
                    writer = pq.ParquetWriter(str(SANGA_FOOD_PARQUET), table.schema)
                writer.write_table(table)
                food_rows += len(food)

            if file_nulls is not None:
                combined_nulls = (
                    file_nulls if combined_nulls is None else combined_nulls.add(file_nulls, fill_value=0)
                )
            combined_rows += file_rows
            per_file.append(
                {
                    "name": csv_path.name,
                    "encoding": enc,
                    "bytes": csv_path.stat().st_size,
                    "rows": file_rows,
                }
            )
    finally:
        if writer is not None:
            writer.close()

    column_stats = _column_stats(columns, sample_dtypes, combined_nulls, combined_rows)
    result = {
        "name": SANGA_DIR.name,
        "encoding": encoding,
        "bytes": sum(item["bytes"] for item in per_file),
        "rows": combined_rows,
        "food_rows": food_rows,
        "columns": column_stats,
        "files": per_file,
        "parquet": str(SANGA_FOOD_PARQUET.as_posix()),
    }
    return result


def _profile_and_write(src: Path, dest: Path, keep_cols: list[str], force: bool) -> dict:
    enc = detect_encoding(src)
    header = read_csv_header(src, enc)
    sample = pd.read_csv(src, encoding=enc, nrows=3000, low_memory=False)
    sample_dtypes = {col: str(sample[col].dtype) for col in sample.columns}
    keep = [col for col in keep_cols if col in header]

    if dest.exists() and not force:
        rows = _parquet_rows(dest)
        # 결측은 원본을 다시 세야 정확하므로, 캐시된 profile이 있으면 run_all이 재사용한다.
        return {
            "name": src.name,
            "encoding": enc,
            "bytes": src.stat().st_size,
            "rows": rows,
            "columns": _column_stats(header, sample_dtypes, None, rows),
            "parquet": str(dest.as_posix()),
            "profile_incomplete": True,
        }

    writer = None
    n = 0
    nulls: pd.Series | None = None
    try:
        for chunk in iter_csv_chunks(src, encoding=enc, chunksize=80_000):
            miss = chunk.apply(missing_mask).sum()
            nulls = miss if nulls is None else nulls.add(miss, fill_value=0)
            n += len(chunk)
            table = pa.Table.from_pandas(chunk.loc[:, keep], preserve_index=False)
            if writer is None:
                if dest.exists():
                    dest.unlink()
                writer = pq.ParquetWriter(str(dest), table.schema)
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()

    return {
        "name": src.name,
        "encoding": enc,
        "bytes": src.stat().st_size,
        "rows": n,
        "columns": _column_stats(header, sample_dtypes, nulls, n),
        "parquet": str(dest.as_posix()),
    }


def _column_stats(
    header: list[str],
    sample_dtypes: dict[str, str],
    nulls: pd.Series | None,
    rows: int,
) -> list[dict]:
    stats = []
    for col in header:
        missing = int(nulls[col]) if nulls is not None and col in nulls.index else None
        rate = (missing / rows) if missing is not None and rows else None
        stats.append(
            {
                "name": col,
                "dtype_sample": sample_dtypes.get(col, "unknown"),
                "missing": missing,
                "missing_rate": rate,
            }
        )
    return stats


def _load_complete_profile() -> dict | None:
    needed = (
        LICENSE_GENERAL_PARQUET,
        LICENSE_REST_PARQUET,
        POPULATION_PARQUET,
        SANGA_FOOD_PARQUET,
        PROFILE_JSON,
    )
    if any(not path.exists() for path in needed):
        return None
    try:
        payload = json.loads(PROFILE_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    files = payload.get("files") or []
    if not files:
        return None
    columns = files[0].get("columns") or []
    if columns and columns[0].get("missing_rate") is not None:
        return payload
    return None


def _parquet_rows(path: Path) -> int:
    parquet = pq.ParquetFile(str(path))
    return parquet.metadata.num_rows


def _cached_sanga_meta(csv_files: list[Path]) -> dict | None:
    if not PROFILE_JSON.exists() or not SANGA_FOOD_PARQUET.exists():
        return None
    try:
        payload = json.loads(PROFILE_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    sanga = payload.get("sanga")
    if not sanga:
        return None
    return sanga


if __name__ == "__main__":
    run(force=True)
    print(f"wrote {PROFILE_JSON}")
