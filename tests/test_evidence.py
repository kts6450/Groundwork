import json

import pytest

from src.scoring import evidence as evidence_module
from src.scoring.evidence import evidence_sentence, load_evidence

PAYLOAD = {
    "train_from": "2015-01-01",
    "train_to": "2019-12-31",
    "test_from": "2020-01-01",
    "test_to": "2022-12-31",
    "train_n": 445256,
    "test_n": 286800,
    "auc_category": 0.5457,
    "auc_region": 0.5703,
    "grades": {
        "합격": {"n": 73055, "actual_3y": 0.7013},
        "위험": {"n": 50722, "actual_3y": 0.5958},
    },
}


@pytest.fixture()
def evidence_file(tmp_path, monkeypatch):
    path = tmp_path / "backtest_evidence.json"
    monkeypatch.setattr(evidence_module, "BACKTEST_EVIDENCE_JSON", path)
    return path


def test_load_evidence_returns_none_when_backtest_has_not_run(evidence_file) -> None:
    assert load_evidence() is None


def test_load_evidence_reads_grades(evidence_file) -> None:
    evidence_file.write_text(json.dumps(PAYLOAD), encoding="utf-8")

    loaded = load_evidence()

    assert loaded is not None
    assert loaded.train_n == 445256
    assert loaded.for_grade("합격").n == 73055
    assert loaded.for_grade("주의") is None


def test_evidence_sentence_is_empty_without_backtest() -> None:
    assert evidence_sentence("합격", None) == ""


def test_evidence_sentence_quotes_the_grade_and_actual_rate(evidence_file) -> None:
    evidence_file.write_text(json.dumps(PAYLOAD), encoding="utf-8")

    text = evidence_sentence("합격", load_evidence())

    assert "2020~2022년" in text
    assert "73,055곳" in text
    assert "70.1%" in text


def test_evidence_sentence_empty_for_unknown_grade(evidence_file) -> None:
    evidence_file.write_text(json.dumps(PAYLOAD), encoding="utf-8")

    assert evidence_sentence("주의", load_evidence()) == ""
