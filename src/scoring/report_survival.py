"""reports/survival.md, reports/categories.md 생성."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.scoring.categories import CATEGORIES, EXCLUDE, JUDGMENT_NOTES
from src.scoring.survival import CohortSpec

DROP_LABELS = {
    "permit_out_of_window": "인허가일자가 코호트 기간 밖(또는 없음)",
    "closed_status_without_date": "폐업 상태인데 폐업일자 없음",
    "closed_before_permit": "폐업일자가 인허가일자보다 이름",
    "category_excluded_or_unmapped": "업종 제외 또는 미매핑",
    "region_unparsed": "주소에서 시도·시군구를 못 읽음 (시도·시군구 표에서만 제외)",
}

EXAMPLE_CATEGORIES = ("카페", "한식", "치킨", "주점")
EXAMPLE_MIN_N = 30


def _fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if pd.isna(value):
            return ""
        return f"{value:.1%}" if 0 <= value <= 1 else f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def md_table(df: pd.DataFrame, columns: dict[str, str] | None = None) -> str:
    if columns:
        df = df[list(columns)].rename(columns=columns)
    header = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "| " + " | ".join("---" for _ in df.columns) + " |"
    rows = ["| " + " | ".join(_fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([header, sep, *rows])


def _rate_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in [c for c in out.columns if c.startswith("surv_")]:
        out[col] = out[col].astype(float)
    out["n"] = out["n"].astype(int)
    return out


def write_categories_report(path: Path, coverage: dict, sanga_counts: pd.DataFrame) -> None:
    counts: pd.DataFrame = coverage["counts"]
    lines = [
        "# 업종 공통 분류 (2주 차 초안)",
        "",
        "상가정보 소분류와 인허가 업태구분명을 13개 묶음으로 보낸다. 매핑은 `src/scoring/categories.py`가 기준이고 이 문서는 그 근거 표다.",
        "판단이 들어간 값은 아래 '판단 사항'에 이유를 남겼다. 바꾸려면 코드의 표를 고치고 `python -m src.scoring.run_survival`을 다시 돌린다.",
        "",
        "## 묶음",
        "",
        ", ".join(CATEGORIES) + f" (+ `{EXCLUDE}`: 생존률 대상이 아닌 값)",
        "",
        "EDA가 제안한 10개(한식·중식·일식·양식·분식·회·육류구이·주점·카페·기타)에 **치킨, 피자·버거, 베이커리·디저트**를 더했다.",
        "치킨은 창업 빈도가 높고, 피자·버거는 상가 소분류에 따로 있으며, 베이커리는 카페 생존률에 섞이면 안 되기 때문이다.",
        "",
        "## 묶음별 원본 값",
        "",
    ]
    for bucket in [*CATEGORIES, EXCLUDE]:
        lic = counts[counts["category"] == bucket].sort_values("n", ascending=False)
        sng = sanga_counts[sanga_counts["category"] == bucket]
        lic_text = ", ".join(f"{r.business_type}({r.source[:2]} {r.n:,})" for r in lic.itertuples()) or "-"
        sng_text = ", ".join(f"{getattr(r, '상권업종소분류명')}({r.n:,})" for r in sng.itertuples()) or "-"
        lines += [f"### {bucket}", "", f"- 인허가 업태: {lic_text}", f"- 상가 소분류: {sng_text}", ""]

    lines += ["## 판단 사항", "", "| 원본 값 | 출처 | 묶음 | 이유 |", "| --- | --- | --- | --- |"]
    lines += [f"| {v} | {s} | {b} | {r} |" for v, s, b, r in JUDGMENT_NOTES]

    unmapped: pd.DataFrame = coverage["unmapped"]
    lines += ["", "## 미매핑 값 (인허가)", ""]
    if unmapped.empty:
        lines.append("없음. 모든 업태구분명이 매핑표에 있다.")
    else:
        lines.append(md_table(unmapped, {"source": "파일", "business_type": "업태구분명", "n": "행 수"}))

    sanga_unmapped = sanga_counts[sanga_counts["category"].isna()]
    lines += ["", "## 미매핑 값 (상가 소분류)", ""]
    if sanga_unmapped.empty:
        lines.append("없음. 소분류 43개가 모두 매핑표에 있다.")
    else:
        lines.append(md_table(sanga_unmapped, {"상권업종중분류명": "중분류", "상권업종소분류명": "소분류", "n": "행 수"}))

    lines += ["", "## 인허가 묶음별 행 수", ""]
    by_bucket = counts.groupby(["category", "source"], dropna=False)["n"].sum().unstack(fill_value=0).reset_index()
    by_bucket["category"] = by_bucket["category"].fillna("(미매핑)")
    by_bucket["합계"] = by_bucket.drop(columns="category").sum(axis=1)
    by_bucket = by_bucket.sort_values("합계", ascending=False)
    lines.append(md_table(by_bucket.rename(columns={"category": "묶음"})))
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def _examples(sgg: pd.DataFrame, min_n: int) -> list[str]:
    lines: list[str] = []
    cols = {"sido": "시도", "sgg": "시군구", "n": "n", "surv_1y": "1년", "surv_3y": "3년"}
    for cat in EXAMPLE_CATEGORIES:
        sub = sgg[(sgg["category"] == cat) & (sgg["n"] >= min_n)].sort_values("surv_3y")
        if sub.empty:
            continue
        lines += [
            f"### {cat} (n ≥ {min_n}인 시군구 {len(sub):,}개)",
            "",
            "3년 생존률 하위 5",
            "",
            md_table(sub.head(5), cols),
            "",
            "3년 생존률 상위 5",
            "",
            md_table(sub.tail(5).iloc[::-1], cols),
            "",
        ]
    return lines


def write_survival_report(
    path: Path,
    *,
    spec: CohortSpec,
    min_n: int,
    total_rows: int,
    dropped: dict[str, int],
    cohort: pd.DataFrame,
    nation: pd.DataFrame,
    sido: pd.DataFrame,
    sgg: pd.DataFrame,
    sido_small: int,
    sgg_small: int,
) -> None:
    nation = _rate_cols(nation).sort_values("surv_3y", ascending=False)
    sido = _rate_cols(sido)
    sgg = _rate_cols(sgg)
    region_ok = len(cohort) - dropped.get("region_unparsed", 0)
    last_observable = (spec.opened_to + pd.DateOffset(years=max(spec.horizons))).date()
    n_sgg_units = sgg[["sido", "sgg"]].drop_duplicates().shape[0]
    q = sgg["surv_3y"].quantile([0.25, 0.5, 0.75])

    lines = [
        "# 생존표 (2주 차)",
        "",
        "인허가 개·폐업 이력으로 **시군구 × 업종**의 1년·3년 생존률을 만들었다. 검증기(주소·업태 → 합격/주의/위험)의 기준표다.",
        "행정동 단위는 인허가에 동 코드가 없어 경계 파일 공간 조인 이후로 미룬다(EDA 결론).",
        "",
        "## 정의",
        "",
        f"- 코호트: 인허가일자가 **{spec.opened_from.date()} ~ {spec.opened_to.date()}** 인 점포",
        f"- 데이터 기준일: {spec.data_cutoff.date()} (인허가일자 최대값). opened_to + 3년 = {last_observable} ≤ 기준일이므로 모든 점포가 3년을 관측 가능",
        "- h년 생존: 폐업일자가 없거나, 폐업일자 > 인허가일자 + h년",
        f"- 표본 {min_n}개 미만 그룹은 표에서 제외",
        "- 시군구 키: 도로명주소(없으면 지번주소)에서 정규식으로 시도·시군구를 읽음. 강원도→강원특별자치도 등 옛 시도명은 합침. 세종은 시 전체를 한 시군구로 봄. `전남광주통합특별시`는 광주 5개 구→광주광역시, 나머지 시·군→전라남도로 나눔. 일반구가 있는 시(수원·성남·화성 동탄구 등)만 시+구를 남기고, 유구읍·행구동처럼 구로 끝나는 읍·동은 시로 되돌림",
        "- 코호트 시작을 2015년으로 잡은 이유: 검증기는 최근 10년 안의 생존을 보여주는 게 맞고, 그 이전은 등록 관행이 달라 보인다(EDA 연도별 표). 기간은 `run_survival.py`의 `SPEC`에서 바꾼다",
        "",
        "## 행 수 흐름",
        "",
        f"- 인허가 원본(일반+휴게): {total_rows:,}",
    ]
    lines += [f"- 제외 · {DROP_LABELS.get(key, key)}: {n:,}" for key, n in dropped.items()]
    lines += [
        f"- **코호트: {len(cohort):,}** (이 중 시도·시군구 파싱 성공 {region_ok:,})",
        "",
        "## 전국 업종별 생존률",
        "",
        md_table(nation, {"category": "업종", "n": "n", "surv_1y": "1년 생존", "surv_3y": "3년 생존"}),
        "",
        "## 시도 × 업종 3년 생존률",
        "",
    ]
    pivot = sido.pivot(index="sido", columns="category", values="surv_3y")
    pivot = pivot[[c for c in CATEGORIES if c in pivot.columns]]
    pivot_txt = pivot.map(lambda v: "" if pd.isna(v) else f"{v:.0%}").reset_index().rename(columns={"sido": "시도"})
    lines += [md_table(pivot_txt), "", f"(n<{min_n}으로 빠진 시도×업종 그룹: {sido_small})", ""]

    lines += [
        "## 시군구 × 업종",
        "",
        f"- 표 크기: {len(sgg):,} 행 (시군구 {n_sgg_units:,}개 × 업종). n<{min_n}으로 빠진 그룹 {sgg_small:,}개",
        f"- 3년 생존률 분포: 최소 {sgg['surv_3y'].min():.1%}, 25% {q[0.25]:.1%}, 중위 {q[0.5]:.1%}, 75% {q[0.75]:.1%}, 최대 {sgg['surv_3y'].max():.1%}",
        "",
    ]
    lines += _examples(sgg, EXAMPLE_MIN_N)

    lines += [
        "## 다음 단계 판단에 필요한 사항",
        "",
        "### 검증기 등급 기준 (제안)",
        "",
        "- 입력: 주소(→ 시군구) + 업태(→ 묶음). 출력: 해당 시군구×업종 3년 생존률과 전국 같은 업종 생존률의 차이",
        "- 제안: 차이 ≥ +5%p → 합격, -5%p ~ +5%p → 주의, ≤ -5%p → 위험. 임계값은 위 시군구 3년 생존률 분포의 사분위에 맞춰 조정",
        f"- 시군구×업종이 n<{min_n}이면 시도×업종으로, 그것도 없으면 전국 업종으로 내려서 답하고 근거 수준을 함께 표시",
        "",
        "### 한계",
        "",
        "- 시군구는 주소 정규식이라 파싱 실패가 있고(위 행 수 흐름), 시군구 통합·분리 이력은 반영하지 않음",
        "- 치킨(업태 통닭(치킨))은 2015년 이후 신규 등록이 거의 없어 코호트 n이 작다. 최근 치킨집은 한식·호프/통닭으로 신고됐을 가능성이 큼",
        "- 화성시처럼 구가 생긴 곳은 동탄구 등과 구 없는 '화성시' 잔여 주소가 따로 잡힌다. 잔여 칸 n은 작다",
        "- '기타' 묶음은 인허가 기타·기타 휴게음식점·일반조리판매를 합친 것으로 구성이 불명. 검증기에서 기타는 참고용으로만",
        "- 폐업일자가 없는 폐업 점포는 제외했으므로 생존률이 아주 조금 높게 나옴",
        "- 인허가 업태는 사업자가 신고한 값이라 실제 메뉴와 다를 수 있음",
        "",
        "### 확인 필요",
        "",
        "- 개방자치단체코드(7자리)와 행정표준 시군구코드 대응표를 확보하면 주소 파싱 대신 코드로 시군구를 붙일 수 있음",
        "- 상가정보(현재 영업 점포)와 인허가 코호트의 업종 비율이 시군구별로 얼마나 다른지. 다르면 매핑표 재검토",
        "- 행정동 경계 파일 입수 시점. 동 단위 생존표는 그 다음",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
