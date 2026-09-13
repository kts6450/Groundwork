"""백테스트에서 나온 등급별 실제 성적.

검증기가 "합격"이라고 말할 때, 과거에 같은 등급을 받은 점포가 실제로 어땠는지
함께 보여주기 위한 값이다. `python -m src.scoring.run_backtest`가 이 파일을 갱신한다.
숫자를 손으로 고치지 말 것.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.scoring.paths import BACKTEST_EVIDENCE_JSON


@dataclass(frozen=True)
class GradeEvidence:
    grade: str
    n: int
    actual_3y: float


@dataclass(frozen=True)
class Evidence:
    train_from: str
    train_to: str
    test_from: str
    test_to: str
    train_n: int
    test_n: int
    auc_category: float
    auc_region: float
    grades: dict[str, GradeEvidence]

    def for_grade(self, grade: str) -> GradeEvidence | None:
        return self.grades.get(grade)


def load_evidence() -> Evidence | None:
    """백테스트를 아직 돌리지 않았으면 None. 검증기는 그 경우 근거 문장을 생략한다."""
    if not BACKTEST_EVIDENCE_JSON.exists():
        return None
    raw = json.loads(BACKTEST_EVIDENCE_JSON.read_text(encoding="utf-8"))
    grades = {
        key: GradeEvidence(grade=key, n=int(value["n"]), actual_3y=float(value["actual_3y"]))
        for key, value in raw["grades"].items()
    }
    return Evidence(
        train_from=raw["train_from"],
        train_to=raw["train_to"],
        test_from=raw["test_from"],
        test_to=raw["test_to"],
        train_n=int(raw["train_n"]),
        test_n=int(raw["test_n"]),
        auc_category=float(raw["auc_category"]),
        auc_region=float(raw["auc_region"]),
        grades=grades,
    )


def save_evidence(payload: dict) -> None:
    BACKTEST_EVIDENCE_JSON.parent.mkdir(parents=True, exist_ok=True)
    BACKTEST_EVIDENCE_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )


def evidence_sentence(grade: str, evidence: Evidence | None) -> str:
    """등급 하나에 대한 과거 성적 한 문장."""
    if evidence is None:
        return ""
    row = evidence.for_grade(grade)
    if row is None:
        return ""
    return (
        f"{evidence.test_from[:4]}~{evidence.test_to[:4]}년에 개업한 점포로 확인해 보면, "
        f"같은 '{grade}' 판정을 받은 {row.n:,}곳의 3년 생존은 {row.actual_3y:.1%}였다."
    )
