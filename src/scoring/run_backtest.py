"""백테스트 실행 → reports/backtest.md.

실행: python -m src.scoring.run_backtest
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.scoring import paths
from src.scoring.backtest import BacktestSpec, run_backtest
from src.scoring.evidence import save_evidence
from src.scoring.metrics import brier_score, calibration_bins, lift_by_bucket, roc_auc
from src.scoring.report_survival import md_table
from src.scoring.run_survival import load_license, prepare
from src.scoring.survival import CohortSpec

DATA_CUTOFF = pd.Timestamp("2026-09-09")

TRAIN = CohortSpec(
    opened_from=pd.Timestamp("2015-01-01"),
    opened_to=pd.Timestamp("2019-12-31"),
    data_cutoff=DATA_CUTOFF,
)
TEST = CohortSpec(
    opened_from=pd.Timestamp("2020-01-01"),
    opened_to=pd.Timestamp("2022-12-31"),
    data_cutoff=DATA_CUTOFF,
)
SPEC = BacktestSpec(train=TRAIN, test=TEST)

BASELINES = {
    "전체 평균 (업종·지역 무시)": "pred_overall",
    "업종만 (전국 업종별)": "pred_category",
    "업종 + 지역 (검증기)": "pred_region",
}


def _metrics_table(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, col in BASELINES.items():
        rows.append(
            {
                "예측 방식": label,
                "AUC": roc_auc(scored[col], scored["survived"]),
                "Brier (낮을수록 좋음)": brier_score(scored[col], scored["survived"]),
            }
        )
    frame = pd.DataFrame(rows)
    frame["AUC"] = frame["AUC"].map(lambda v: f"{v:.4f}")
    frame["Brier (낮을수록 좋음)"] = frame["Brier (낮을수록 좋음)"].map(lambda v: f"{v:.4f}")
    return frame


def _grade_table(scored: pd.DataFrame) -> pd.DataFrame:
    lift = lift_by_bucket(scored, "grade", "survived")
    order = {"합격": 0, "주의": 1, "위험": 2}
    lift["_o"] = lift["grade"].map(order)
    lift = lift.sort_values("_o").drop(columns="_o")
    lift["n"] = lift["n"].astype(int)
    lift["actual"] = lift["actual"].map(lambda v: f"{v:.1%}")
    lift["diff_vs_all"] = lift["diff_vs_all"].map(lambda v: f"{v * 100:+.1f}%p" if pd.notna(v) else "")
    return lift.rename(
        columns={"grade": "등급", "n": "평가 점포 수", "actual": "실제 3년 생존", "diff_vs_all": "전체 대비"}
    )


def _by_level_table(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for level in ("시군구", "시도", "전국"):
        sub = scored[scored["level"] == level]
        if sub.empty:
            continue
        rows.append(
            {
                "표 수준": level,
                "평가 점포 수": len(sub),
                "AUC": f"{roc_auc(sub['pred_region'], sub['survived']):.4f}",
                "실제 3년 생존": f"{sub['survived'].mean():.1%}",
            }
        )
    return pd.DataFrame(rows)


def _category_table(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for category, sub in scored.groupby("category"):
        if len(sub) < 200:
            continue
        rows.append(
            {
                "업종": category,
                "평가 점포 수": len(sub),
                "AUC": roc_auc(sub["pred_region"], sub["survived"]),
                "실제 3년 생존": sub["survived"].mean(),
            }
        )
    frame = pd.DataFrame(rows).sort_values("AUC", ascending=False)
    frame["AUC"] = frame["AUC"].map(lambda v: f"{v:.4f}")
    frame["실제 3년 생존"] = frame["실제 3년 생존"].map(lambda v: f"{v:.1%}")
    return frame


def write_report(path: Path, result: dict) -> None:
    spec: BacktestSpec = result["spec"]
    scored: pd.DataFrame = result["scored"]
    train = result["train_cohort"]

    auc_region = roc_auc(scored["pred_region"], scored["survived"])
    auc_category = roc_auc(scored["pred_category"], scored["survived"])
    grade = _grade_table(scored)
    pass_rate = scored.loc[scored["grade"] == "합격", "survived"].mean()
    risk_rate = scored.loc[scored["grade"] == "위험", "survived"].mean()

    calib = calibration_bins(scored["pred_region"], scored["survived"], bins=10)
    calib_txt = calib.assign(
        predicted=calib["predicted"].map(lambda v: f"{v:.1%}"),
        actual=calib["actual"].map(lambda v: f"{v:.1%}"),
        n=calib["n"].astype(int),
    ).rename(columns={"bin": "예측 구간", "n": "점포 수", "predicted": "평균 예측", "actual": "실제"})

    lines = [
        "# 백테스트 (3주 차)",
        "",
        "생존표가 **그 뒤에 개업한 점포**의 폐업을 실제로 가려내는지 측정했다.",
        "학습 코호트로만 표를 만들고, 평가 코호트의 폐업 정보는 표에 넣지 않는다. 미래를 훔쳐보지 않는다는 뜻이다.",
        "",
        "## 설계",
        "",
        f"- 학습 코호트: {spec.train.opened_from.date()} ~ {spec.train.opened_to.date()} 개업 · {len(train):,}곳 → 이걸로 시군구×업종 생존표를 만든다",
        f"- 평가 코호트: {spec.test.opened_from.date()} ~ {spec.test.opened_to.date()} 개업 · {len(scored):,}곳 → 표의 값을 예측으로 붙이고 실제 3년 생존과 비교",
        f"- 데이터 기준일 {DATA_CUTOFF.date()}. 평가 코호트 마지막 개업 + 3년 = {(spec.test.opened_to + pd.DateOffset(years=3)).date()} 이므로 전원 3년 관측 가능",
        f"- 표본 {spec.min_n}개 미만 칸은 만들지 않고, 그 경우 시도 → 전국 순으로 내려간다 (검증기와 같은 규칙)",
        "",
        "## 예측 방식별 성능",
        "",
        md_table(_metrics_table(scored)),
        "",
        "AUC는 무작위로 고른 '살아남은 점포'와 '문 닫은 점포' 한 쌍에서 살아남은 쪽에 더 높은 점수를 줄 확률이다. 0.5는 동전 던지기다.",
        f"지역을 넣으면 업종만 쓸 때보다 AUC가 {auc_category:.4f} → {auc_region:.4f}로 움직인다.",
        "",
        "## 등급이 실제 결과와 이어지는가",
        "",
        md_table(grade),
        "",
    ]
    if pd.notna(pass_rate) and pd.notna(risk_rate):
        lines += [
            f"합격 등급 점포의 실제 3년 생존은 {pass_rate:.1%}, 위험 등급은 {risk_rate:.1%}로 **{(pass_rate - risk_rate) * 100:.1f}%p** 차이가 난다.",
            "이 격차가 검증기가 실제로 뭔가를 가려낸다는 근거다.",
            "",
        ]
    lines += [
        "## 폴백 수준별",
        "",
        md_table(_by_level_table(scored)),
        "",
        "## 업종별 (평가 200곳 이상)",
        "",
        md_table(_category_table(scored)),
        "",
        "## 예측 보정 (예측 확률 구간별 실제)",
        "",
        md_table(calib_txt[["예측 구간", "점포 수", "평균 예측", "실제"]]),
        "",
        "평균 예측과 실제가 가까울수록 예측 확률을 그대로 사용자에게 보여줄 수 있다.",
        "",
        "## 읽는 법과 한계",
        "",
        "- AUC가 0.5를 크게 넘지 않아도 등급 간 생존률 격차가 크면 검증기는 쓸모가 있다. 개별 점포의 운명은 상권보다 운영이 좌우하기 때문이다",
        "- 평가 코호트가 2020~2022년이라 코로나 기간과 겹친다. 학습 코호트(2015~2019)와 환경이 다르므로 성능이 낮게 나올 수 있다",
        "- 지역·업종만 쓰고 점포 규모·브랜드·임대료는 쓰지 않는다. 이 지표들이 없는 것이 성능 상한을 만든다",
        "- 폐업일자가 없는 폐업 점포는 두 코호트에서 모두 빠졌다",
        "",
        "## 다시 실행",
        "",
        "```powershell",
        "python -m src.scoring.run_backtest",
        "```",
        "",
        "기간을 바꾸려면 `src/scoring/run_backtest.py`의 `TRAIN`·`TEST`를 고친다.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    prepared = prepare(load_license())
    result = run_backtest(prepared, SPEC)
    scored = result["scored"]

    paths.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    keep = ["sido", "sgg", "category", "level", "n_used", "pred_category", "pred_region", "grade", "survived"]
    scored[keep].to_parquet(paths.BACKTEST_SCORED_PARQUET, index=False)
    write_report(paths.BACKTEST_REPORT_MD, result)

    auc = roc_auc(scored["pred_region"], scored["survived"])
    base = roc_auc(scored["pred_category"], scored["survived"])
    save_evidence(
        {
            "train_from": str(TRAIN.opened_from.date()),
            "train_to": str(TRAIN.opened_to.date()),
            "test_from": str(TEST.opened_from.date()),
            "test_to": str(TEST.opened_to.date()),
            "train_n": len(result["train_cohort"]),
            "test_n": len(scored),
            "auc_category": base,
            "auc_region": auc,
            "grades": {
                g: {"n": int(len(sub)), "actual_3y": float(sub["survived"].mean())}
                for g, sub in scored.groupby("grade")
            },
        }
    )
    print(f"train={len(result['train_cohort']):,} test={len(scored):,}")
    print(f"AUC 업종만={base:.4f} 업종+지역={auc:.4f}")
    for g in ("합격", "주의", "위험"):
        sub = scored[scored["grade"] == g]
        if not sub.empty:
            print(f"  {g}: n={len(sub):,} 실제 3년 생존={sub['survived'].mean():.1%}")
    print(f"wrote {paths.BACKTEST_REPORT_MD.name}")


if __name__ == "__main__":
    main()
