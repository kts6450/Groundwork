"""백테스트 평가 지표.

sklearn을 넣지 않으려고 AUC를 순위 기반(Mann-Whitney U)으로 직접 구현했다.
동점은 평균 순위로 처리한다.
"""

from __future__ import annotations

import pandas as pd


def roc_auc(scores: pd.Series, labels: pd.Series) -> float:
    """labels는 True/False. scores가 높을수록 True일 것으로 본다.

    한쪽 클래스만 있으면 정의되지 않으므로 NaN을 돌려준다.
    """
    frame = pd.DataFrame({"score": scores.astype(float), "label": labels.astype(bool)}).dropna()
    positives = int(frame["label"].sum())
    negatives = len(frame) - positives
    if positives == 0 or negatives == 0:
        return float("nan")
    ranks = frame["score"].rank(method="average")
    rank_sum = float(ranks[frame["label"]].sum())
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def lift_by_bucket(frame: pd.DataFrame, bucket_col: str, label_col: str) -> pd.DataFrame:
    """등급별 실제 생존률. 검증기 등급이 실제 결과와 이어지는지 보는 표."""
    grouped = (
        frame.groupby(bucket_col, dropna=False)
        .agg(n=(label_col, "size"), actual=(label_col, "mean"))
        .reset_index()
    )
    overall = float(frame[label_col].mean())
    grouped["diff_vs_all"] = grouped["actual"] - overall
    return grouped


def brier_score(predicted: pd.Series, labels: pd.Series) -> float:
    """예측 확률과 실제의 제곱 오차 평균. 낮을수록 좋다."""
    frame = pd.DataFrame({"p": predicted.astype(float), "y": labels.astype(float)}).dropna()
    if frame.empty:
        return float("nan")
    return float(((frame["p"] - frame["y"]) ** 2).mean())


def calibration_bins(predicted: pd.Series, labels: pd.Series, bins: int = 10) -> pd.DataFrame:
    """예측 확률 구간별 평균 예측과 실제. 예측이 현실과 맞는지 본다."""
    frame = pd.DataFrame({"p": predicted.astype(float), "y": labels.astype(float)}).dropna()
    if frame.empty:
        return pd.DataFrame(columns=["bin", "n", "predicted", "actual"])
    frame["bin"] = pd.qcut(frame["p"], q=bins, duplicates="drop")
    out = (
        frame.groupby("bin", observed=True)
        .agg(n=("y", "size"), predicted=("p", "mean"), actual=("y", "mean"))
        .reset_index()
    )
    out["bin"] = out["bin"].astype(str)
    return out
