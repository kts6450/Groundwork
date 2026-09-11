from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

ENCODINGS = ("cp949", "utf-8-sig", "utf-8")


def detect_encoding(path: Path) -> str:
    """프로젝트 규칙 순서로 첫 줄을 읽을 수 있는 인코딩을 고른다."""
    raw = _first_line_bytes(path)
    last_error: UnicodeDecodeError | None = None
    decoded: list[tuple[str, str]] = []
    for enc in ENCODINGS:
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        decoded.append((enc, text))
        if _looks_like_header(text):
            return enc
    if decoded:
        return decoded[0][0]
    raise ValueError(f"인코딩을 확인하지 못함: {path}") from last_error


def read_csv_header(path: Path, encoding: str | None = None) -> list[str]:
    enc = encoding or detect_encoding(path)
    with path.open("r", encoding=enc, newline="") as handle:
        row = next(csv.reader(handle))
    return [col.strip() for col in row]


def iter_csv_chunks(
    path: Path,
    encoding: str | None = None,
    usecols: list[str] | None = None,
    chunksize: int = 100_000,
    dtype: str | dict | None = "string",
) -> Iterator[pd.DataFrame]:
    enc = encoding or detect_encoding(path)
    reader = pd.read_csv(
        path,
        encoding=enc,
        usecols=usecols,
        chunksize=chunksize,
        dtype=dtype,
        low_memory=False,
    )
    yield from reader


def missing_mask(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    return text.isna() | text.isin(["", "None", "<NA>", "nan", "NaN"])


def missing_rate(series: pd.Series) -> float:
    if len(series) == 0:
        return 0.0
    return float(missing_mask(series).mean())


def _first_line_bytes(path: Path) -> bytes:
    with path.open("rb") as handle:
        line = handle.readline()
    return line.rstrip(b"\r\n")


def _looks_like_header(text: str) -> bool:
    hangul = sum(1 for char in text if "가" <= char <= "힣")
    return hangul >= 2
