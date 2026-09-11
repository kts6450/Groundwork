from __future__ import annotations

import pandas as pd


def code_digit_lengths(series: pd.Series) -> dict:
    text = series.astype("string")
    is_null = text.isna() | (text.str.strip() == "")
    rest = text[~is_null].str.strip()
    is_digit = rest.str.fullmatch(r"\d+")
    lengths = rest[is_digit].str.len().value_counts()
    result = {int(length): int(count) for length, count in lengths.items()}
    result["non_digit"] = int((~is_digit).sum())
    result["null"] = int(is_null.sum())
    return result


def admin_code_join(sanga: pd.Series, population: pd.Series) -> dict:
    sanga_codes = {
        code
        for code in sanga.astype("string").str.strip().dropna().unique()
        if str(code).isdigit()
    }
    pop_codes = {
        code
        for code in population.astype("string").str.strip().dropna().unique()
        if str(code).isdigit()
    }
    pop_first8 = {code[:8] for code in pop_codes if len(code) >= 8}
    matched = sanga_codes & pop_first8
    return {
        "direct_join": bool(sanga_codes) and sanga_codes <= pop_codes,
        "join_on_pop_first8": bool(matched),
        "sanga_matched_via_first8": len(matched),
        "sanga_unmatched_via_first8": len(sanga_codes - pop_first8),
        "sanga_unique": len(sanga_codes),
        "pop_unique": len(pop_codes),
        "sanga_sample": sorted(sanga_codes)[:5],
        "pop_sample": sorted(pop_codes)[:5],
    }
