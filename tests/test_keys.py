import pandas as pd

from src.eda.keys import admin_code_join, code_digit_lengths


def test_code_digit_lengths_counts_digits_only() -> None:
    series = pd.Series(["11200660", "1111051500", "11200660", None, "abc"])

    stats = code_digit_lengths(series)

    assert stats[8] == 2
    assert stats[10] == 1
    assert stats["non_digit"] == 1
    assert stats["null"] == 1


def test_admin_code_join_not_direct_when_lengths_differ() -> None:
    sanga = pd.Series(["11200660", "11110515"])
    population = pd.Series(["1120066000", "1111051500", "1111051800"])

    result = admin_code_join(sanga, population)

    assert result["direct_join"] is False
    assert result["join_on_pop_first8"] is True
    assert result["sanga_matched_via_first8"] == 2
    assert result["sanga_unmatched_via_first8"] == 0


def test_admin_code_join_reports_unmatched_sanga_codes() -> None:
    sanga = pd.Series(["99999999"])
    population = pd.Series(["1111051500"])

    result = admin_code_join(sanga, population)

    assert result["sanga_matched_via_first8"] == 0
    assert result["sanga_unmatched_via_first8"] == 1
