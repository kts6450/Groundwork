from __future__ import annotations

import pandas as pd


def parse_license_date(series: pd.Series) -> pd.Series:
    raw = series.astype("string").str.strip()
    hyphen = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")
    compact = pd.to_datetime(raw, format="%Y%m%d", errors="coerce")
    return hyphen.fillna(compact)


def open_at(permit: pd.Series, closed: pd.Series, as_of: pd.Timestamp) -> pd.Series:
    """인허가일자 <= T 이고 (폐업일자 없음 또는 폐업일자 > T)."""
    as_of = pd.Timestamp(as_of)
    opened = permit.notna() & (permit <= as_of)
    still_open = closed.isna() | (closed > as_of)
    return opened & still_open
