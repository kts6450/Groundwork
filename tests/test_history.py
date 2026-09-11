import pandas as pd

from src.eda.history import open_at, parse_license_date


def test_parse_license_date_accepts_hyphen_and_digits() -> None:
    parsed = parse_license_date(pd.Series(["2017-02-28", "20191031", "", None]))

    assert list(parsed.dt.strftime("%Y-%m-%d"))[:2] == ["2017-02-28", "2019-10-31"]
    assert parsed.isna().tolist()[2:] == [True, True]


def test_open_at_keeps_store_without_close_date() -> None:
    permit = parse_license_date(pd.Series(["2020-01-01"]))
    closed = parse_license_date(pd.Series([None]))

    assert open_at(permit, closed, pd.Timestamp("2022-01-01")).tolist() == [True]


def test_open_at_excludes_not_yet_opened_and_already_closed() -> None:
    permit = parse_license_date(pd.Series(["2022-06-01", "2018-01-01", "2018-01-01"]))
    closed = parse_license_date(pd.Series([None, "2021-12-31", "2022-06-01"]))
    as_of = pd.Timestamp("2022-01-01")

    assert open_at(permit, closed, as_of).tolist() == [False, False, True]


def test_open_at_treats_close_on_as_of_as_closed() -> None:
    permit = parse_license_date(pd.Series(["2019-01-01"]))
    closed = parse_license_date(pd.Series(["2022-01-01"]))

    assert open_at(permit, closed, pd.Timestamp("2022-01-01")).tolist() == [False]
