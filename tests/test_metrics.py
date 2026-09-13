import pandas as pd
import pytest

from src.scoring.metrics import brier_score, calibration_bins, lift_by_bucket, roc_auc


def test_roc_auc_perfect_separation() -> None:
    scores = pd.Series([0.1, 0.2, 0.8, 0.9])
    labels = pd.Series([False, False, True, True])

    assert roc_auc(scores, labels) == pytest.approx(1.0)


def test_roc_auc_reversed_separation() -> None:
    scores = pd.Series([0.9, 0.8, 0.2, 0.1])
    labels = pd.Series([False, False, True, True])

    assert roc_auc(scores, labels) == pytest.approx(0.0)


def test_roc_auc_all_tied_is_half() -> None:
    scores = pd.Series([0.5] * 6)
    labels = pd.Series([True, False, True, False, True, False])

    assert roc_auc(scores, labels) == pytest.approx(0.5)


def test_roc_auc_matches_hand_computed_case() -> None:
    # 양성 2개(0.6, 0.4), 음성 2개(0.5, 0.3).
    # 쌍 비교: (0.6>0.5) (0.6>0.3) (0.4<0.5) (0.4>0.3) → 3/4
    scores = pd.Series([0.6, 0.4, 0.5, 0.3])
    labels = pd.Series([True, True, False, False])

    assert roc_auc(scores, labels) == pytest.approx(0.75)


def test_roc_auc_single_class_is_nan() -> None:
    assert pd.isna(roc_auc(pd.Series([0.1, 0.9]), pd.Series([True, True])))


def test_lift_by_bucket_reports_gap_against_overall() -> None:
    frame = pd.DataFrame(
        {
            "grade": ["합격", "합격", "위험", "위험"],
            "survived": [True, True, False, False],
        }
    )

    out = lift_by_bucket(frame, "grade", "survived").set_index("grade")

    assert out.loc["합격", "actual"] == pytest.approx(1.0)
    assert out.loc["위험", "actual"] == pytest.approx(0.0)
    assert out.loc["합격", "diff_vs_all"] == pytest.approx(0.5)


def test_brier_score_is_zero_when_prediction_is_exact() -> None:
    assert brier_score(pd.Series([1.0, 0.0]), pd.Series([True, False])) == pytest.approx(0.0)


def test_brier_score_penalises_confident_mistakes() -> None:
    assert brier_score(pd.Series([0.0, 1.0]), pd.Series([True, False])) == pytest.approx(1.0)


def test_calibration_bins_returns_one_row_per_bin() -> None:
    predicted = pd.Series([i / 100 for i in range(100)])
    labels = pd.Series([i >= 50 for i in range(100)])

    out = calibration_bins(predicted, labels, bins=4)

    assert len(out) == 4
    assert out["n"].sum() == 100
    assert out["predicted"].is_monotonic_increasing


def test_lift_diff_is_a_fraction_not_a_percentage() -> None:
    # 보고서에서 %p로 찍을 때 100을 곱해야 한다는 것을 고정한다.
    frame = pd.DataFrame({"grade": ["합격"] * 7 + ["위험"] * 3, "survived": [True] * 7 + [False] * 3})

    out = lift_by_bucket(frame, "grade", "survived").set_index("grade")

    assert out.loc["합격", "actual"] == pytest.approx(1.0)
    assert out.loc["합격", "diff_vs_all"] == pytest.approx(0.3)
