import pandas as pd
import pytest

from src.scoring.backtest import BacktestSpec, assign_grades, attach_predictions, run_backtest
from src.scoring.survival import CohortSpec

TRAIN = CohortSpec(
    opened_from=pd.Timestamp("2015-01-01"),
    opened_to=pd.Timestamp("2019-12-31"),
    data_cutoff=pd.Timestamp("2026-01-01"),
)
TEST = CohortSpec(
    opened_from=pd.Timestamp("2020-01-01"),
    opened_to=pd.Timestamp("2021-12-31"),
    data_cutoff=pd.Timestamp("2026-01-01"),
)


def _prepared(rows: list[dict]) -> pd.DataFrame:
    base = {"status": "영업/정상", "sido": "서울특별시", "sgg": "종로구", "category": "카페", "closed": None}
    df = pd.DataFrame([{**base, **row} for row in rows])
    df["permit"] = pd.to_datetime(df["permit"])
    df["closed"] = pd.to_datetime(df["closed"])
    return df


def test_spec_rejects_overlapping_train_and_test() -> None:
    with pytest.raises(ValueError):
        BacktestSpec(train=TEST, test=TRAIN)


def test_attach_predictions_falls_back_from_sgg_to_sido_to_nation() -> None:
    tables = {
        "nation": pd.DataFrame({"category": ["카페"], "surv_3y": [0.60], "n": [500]}),
        "sido": pd.DataFrame({"sido": ["서울특별시"], "category": ["카페"], "surv_3y": [0.65], "n": [200]}),
        "sgg": pd.DataFrame(
            {"sido": ["서울특별시"], "sgg": ["종로구"], "category": ["카페"], "surv_3y": [0.70], "n": [50]}
        ),
    }
    test_cohort = pd.DataFrame(
        {
            "sido": ["서울특별시", "서울특별시", "부산광역시"],
            "sgg": ["종로구", "강남구", "해운대구"],
            "category": ["카페", "카페", "카페"],
        }
    )

    out = attach_predictions(test_cohort, tables)

    assert out["level"].tolist() == ["시군구", "시도", "전국"]
    assert out["pred_region"].tolist() == [0.70, 0.65, 0.60]
    assert out["n_used"].tolist() == [50, 200, 500]


def test_assign_grades_uses_gap_against_national_category() -> None:
    frame = pd.DataFrame({"pred_region": [0.70, 0.62, 0.54], "pred_category": [0.60, 0.60, 0.60]})

    assert assign_grades(frame).tolist() == ["합격", "주의", "위험"]


def test_run_backtest_does_not_leak_test_closures_into_tables() -> None:
    # 학습 구간은 전부 생존, 평가 구간은 전부 폐업. 표가 평가 폐업을 반영하면 예측이 낮아진다.
    rows = [{"permit": "2016-01-01"} for _ in range(20)]
    rows += [{"permit": "2020-06-01", "closed": "2020-09-01", "status": "폐업"} for _ in range(20)]

    result = run_backtest(_prepared(rows), BacktestSpec(train=TRAIN, test=TEST))

    assert len(result["train_cohort"]) == 20
    assert len(result["test_cohort"]) == 20
    assert result["scored"]["pred_region"].eq(1.0).all()
    assert not result["scored"]["survived"].any()


def test_run_backtest_scores_every_test_row() -> None:
    rows = [{"permit": "2016-01-01"} for _ in range(15)]
    rows += [{"permit": "2020-06-01"} for _ in range(5)]

    result = run_backtest(_prepared(rows), BacktestSpec(train=TRAIN, test=TEST))
    scored = result["scored"]

    assert len(scored) == 5
    assert scored["pred_region"].notna().all()
    assert set(scored["grade"]) <= {"합격", "주의", "위험"}
