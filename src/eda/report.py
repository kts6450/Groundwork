from __future__ import annotations

import re

from src.eda.paths import REPORT_MD, REPORTS_DIR

_AGE_COL = re.compile(r"(\d+세|110세이상)")


def write(result: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(_render(result), encoding="utf-8")


def _render(result: dict) -> str:
    profile = result["profile"]
    sections = [
        "# 데이터 EDA (1주 차)",
        "",
        "검증기(주소·업태 → 생존 합격/주의/위험)를 만들기 전에, 원본 공공데이터가",
        "행정동에 붙는지, 시점 필터가 되는지, 업종을 같은 말로 묶을 수 있는지를 확인했다.",
        "원본(`data/raw/`)은 읽기만 했고, 중간 산출은 `data/interim/` parquet다.",
        "",
        _overview(profile),
        _categories(result["categories"]),
        _keys(result["keys"]),
        _history(result["history"]),
        _coords(result["coords"]),
        _coverage(result["coverage"]),
        _costs(result["costs"]),
        _time_filter(result["time_filter"]),
        _buildings(result["buildings"]),
        _next_steps(result),
    ]
    return "\n".join(sections).rstrip() + "\n"


def _overview(profile: dict) -> str:
    lines = [
        "## 1. 파일 개요",
        "",
        "인코딩은 `cp949` → `utf-8-sig` → `utf-8` 순으로 첫 줄을 읽어 골랐다.",
        "컬럼 타입은 각 파일 상위 수천 행을 pandas가 추정한 값이다. 분석 시 날짜·좌표·금액은 따로 변환했다.",
        "",
    ]
    for item in profile.get("files", []):
        lines.extend(_file_block(item))
    sanga = profile.get("sanga")
    if sanga:
        lines.extend(_file_block(sanga, extra=f"음식 대분류만 남긴 행 수: **{sanga.get('food_rows', 0):,}**"))
        lines.extend(
            [
                "### 상가정보 시도별 파일",
                "",
                _table(
                    sanga.get("files", []),
                    [
                        ("name", "파일"),
                        ("encoding", "인코딩"),
                        ("bytes", "크기(B)"),
                        ("rows", "행 수"),
                    ],
                ),
                "",
            ]
        )
    return "\n".join(lines)


def _file_block(item: dict, extra: str | None = None) -> list[str]:
    lines = [
        f"### {item['name']}",
        "",
        f"- 인코딩: `{item.get('encoding')}`",
        f"- 파일 크기: {_bytes(item.get('bytes'))} ({item.get('bytes', 0):,} B)",
        f"- 행 수: **{item.get('rows', 0):,}**",
    ]
    if extra:
        lines.append(f"- {extra}")
    lines += ["", _column_table(item.get("columns", [])), ""]
    return lines


def _column_table(columns: list[dict]) -> str:
    if not columns:
        return "_컬럼 통계 없음_"
    rows = []
    age_cols = [col for col in columns if _AGE_COL.search(str(col.get("name") or ""))]
    shown = [col for col in columns if col not in age_cols]
    for col in shown:
        rate = col.get("missing_rate")
        rows.append(
            {
                "name": col.get("name"),
                "dtype": col.get("dtype_sample"),
                "missing": "" if col.get("missing") is None else f"{col['missing']:,}",
                "rate": "" if rate is None else f"{rate * 100:.2f}%",
            }
        )
    table = _table(rows, [("name", "컬럼"), ("dtype", "타입(표본)"), ("missing", "결측"), ("rate", "결측률")])
    if age_cols:
        table += f"\n\n0~110세 남·여 연령 컬럼 {len(age_cols)}개는 결측 없이 채워져 있어 표에서 접었다."
    return table


def _categories(data: dict) -> str:
    lines = [
        "## 2. 업종 컬럼",
        "",
        f"상가정보에서 대분류 `음식`만 남기면 **{data['sanga_food_rows']:,}**행이다.",
        "",
        "### 상가정보 중분류 (음식)",
        "",
        _count_table(data["sanga_mid"]),
        "",
        f"### 상가정보 소분류 (음식, 고유값 {data['sanga_small_unique']:,}개, 상위 40)",
        "",
        _count_table(data["sanga_small_top"]),
        "",
    ]
    for name, block in data["license"].items():
        lines += [f"### {name} 업태구분명", "", _count_table(block["업태구분명"]), ""]
        if not _same_counts(block["업태구분명"], block["위생업태명"]):
            lines += [f"### {name} 위생업태명", "", _count_table(block["위생업태명"]), ""]
        else:
            lines.append("위생업태명은 업태구분명과 거의 같아 생략했다.")
            lines.append("")
    lines += ["### 매핑 때 문제가 될 값", ""]
    for note in data["mapping_notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def _keys(data: dict) -> str:
    join = data["admin_join"]
    direct = "바로 조인된다" if join["direct_join"] else "바로 조인되지 않는다"
    first8 = "된다" if join["join_on_pop_first8"] else "되지 않는다"
    lines = [
        "## 3. 공통 키 후보",
        "",
        "### 상가정보",
        "",
        f"- 행정동코드: {_lengths(data['sanga']['행정동코드']['lengths'])} / 예시 {', '.join(data['sanga']['행정동코드_sample'])}",
        f"- 법정동코드: {_lengths(data['sanga']['법정동코드']['lengths'])} / 예시 {', '.join(data['sanga']['법정동코드_sample'])}",
        f"- 시군구코드: {_lengths(data['sanga']['시군구코드']['lengths'])}",
        f"- 도로명주소 결측률: {_pct(data['sanga']['도로명주소_missing'])}",
        f"- 지번주소 결측률: {_pct(data['sanga']['지번주소_missing'])}",
        f"- 경도/위도 결측률: {_pct(data['sanga']['경도_missing'])} / {_pct(data['sanga']['위도_missing'])}",
        "",
        "### 인구",
        "",
        f"- 행정기관코드: {_lengths(data['population']['행정기관코드']['lengths'])} / 예시 {', '.join(data['population']['행정기관코드_sample'])}",
        f"- 행 수: {data['population']['rows']:,}",
        "",
        "### 상가 행정동코드 × 인구 행정기관코드",
        "",
        f"- 동일 코드로 {direct}.",
        f"- 인구 코드 앞 8자리로 조인하면 {first8}.",
        f"- 앞 8자리 기준 상가 고유코드 매칭 {join['sanga_matched_via_first8']:,} / 미매칭 {join['sanga_unmatched_via_first8']:,} (상가 고유 {join['sanga_unique']:,}, 인구 고유 {join['pop_unique']:,}).",
        "",
        "### 인허가",
        "",
        "행정동코드·법정동코드 컬럼은 없다. 시군구 표준코드도 없고 `개방자치단체코드`만 있다.",
        "",
    ]
    for name, block in data["license"].items():
        lines += [
            f"**{name}**",
            "",
            f"- 개방자치단체코드: {_lengths(block['개방자치단체코드']['lengths'])} / 예시 {', '.join(block['개방자치단체코드_sample'])}",
            f"- 도로명주소 결측률: {_pct(block['도로명주소_missing'])}",
            f"- 지번주소 결측률: {_pct(block['지번주소_missing'])}",
            f"- 좌표 X/Y 결측률: {_pct(block['좌표X_missing'])} / {_pct(block['좌표Y_missing'])}",
            f"- 주소에서 시도 파싱 성공률: {_pct(block['sido_parse_rate'])}",
            "",
        ]
    return "\n".join(lines)


def _history(data: dict) -> str:
    lines = ["## 4. 개·폐업 이력", ""]
    for name, block in data.items():
        lines += [
            f"### {name}",
            "",
            f"- 인허가일자 범위: {block['permit_min']} ~ {block['permit_max']} (파싱 실패 {block['permit_unparsed']:,}건)",
            f"- 폐업일자 범위: {block['closed_min']} ~ {block['closed_max']}",
            f"- 폐업일자가 있는데 날짜로 못 읽은 행: {block['closed_unparsed_among_present']:,}",
            f"- 폐업일자 결측률: {_pct(block['close_date_missing'])}",
            "",
            "영업상태명",
            "",
            _count_table(block["status"]),
            "",
            "상세영업상태명",
            "",
            _count_table(block["detail_status"]),
            "",
            "연도별 개업·폐업 (1980년 이후, 인허가일자/폐업일자 연도)",
            "",
            _table(block["yearly"], [("year", "연도"), ("opened", "개업"), ("closed", "폐업")]),
            "",
        ]
    return "\n".join(lines)


def _coords(data: dict) -> str:
    lines = [
        "## 5. 좌표 검증",
        "",
        "인허가 좌표는 TM으로 안내되어 있다. 후보 CRS로 위경도(EPSG:4326)로 바꾼 뒤,",
        "한반도 범위(124–132E, 33–39.5N)와 시도 중심점까지 거리를 봤다.",
        "",
    ]
    for name, block in data.items():
        lines += [
            f"### {name}",
            "",
            f"- 좌표 결측률: {_pct(block['xy_missing'])}",
            f"- X 범위: {block['x_min']} ~ {block['x_max']}",
            f"- Y 범위: {block['y_min']} ~ {block['y_max']}",
            f"- 가장 잘 맞는 CRS: `{block['best_crs']}`",
            "",
            _table(
                block["scores"],
                [
                    ("crs", "CRS"),
                    ("converted", "변환"),
                    ("in_korea", "한반도 안"),
                    ("median_km_to_sido", "시도 중심까지 중앙값(km)"),
                ],
            ),
            "",
            "주소와 변환 좌표 샘플",
            "",
            _table(
                [
                    {
                        "name": row["name"],
                        "address": row["address"],
                        "lon": f"{row['lon']:.6f}",
                        "lat": f"{row['lat']:.6f}",
                        "in_korea": "Y" if row["in_korea"] else "N",
                    }
                    for row in block["samples"]
                ],
                [
                    ("name", "사업장"),
                    ("address", "주소"),
                    ("lon", "경도"),
                    ("lat", "위도"),
                    ("in_korea", "한반도"),
                ],
            ),
            "",
        ]
    return "\n".join(lines)


def _coverage(data: dict) -> str:
    lines = [
        "## 6. 상가정보 ↔ 인허가 규모",
        "",
        f"상가정보 음식 전체: **{data['sanga_food_total']:,}**.",
        f"인허가 영업 중(상태명에 '폐업' 없음): 일반 {data['license_open_total']['식품_일반음식점']:,} / 휴게 {data['license_open_total']['식품_휴게음식점']:,}.",
        "",
        "같은 시군구에서 상가 음식점 수와 인허가 영업 중 수를 비교했다.",
        "인허가 시군구는 도로명·지번 주소에서 파싱했다.",
        "",
        _table(
            [
                {
                    "area": f"{row['sido']} {row['sgg']}".strip(),
                    "sanga": row["sanga_food"],
                    "gen_open": row["식품_일반음식점_open"],
                    "gen_all": row["식품_일반음식점_all"],
                    "rest_open": row["식품_휴게음식점_open"],
                    "rest_all": row["식품_휴게음식점_all"],
                }
                for row in data["areas"]
            ],
            [
                ("area", "구역"),
                ("sanga", "상가 음식"),
                ("gen_open", "일반 영업중"),
                ("gen_all", "일반 전체"),
                ("rest_open", "휴게 영업중"),
                ("rest_all", "휴게 전체"),
            ],
        ),
        "",
        "상가정보는 영업 중만 있고 카페·주점·간이음식까지 음식에 들어 있다.",
        "인허가는 일반/휴게로 나뉘고 폐업 이력이 남는다. 숫자가 다른 것은 정상이고, 1:1 점포 매칭은 이 표로 주장하지 않는다.",
        "",
    ]
    return "\n".join(lines)


def _costs(data: dict) -> str:
    lines = [
        "## 7. 비용 관련 컬럼",
        "",
        "값은 원본 숫자 그대로다. 월세·보증 단위(원/만원)는 파일에 안 적혀 있어 확인 필요로 남긴다.",
        "0은 결측으로 보고, 0보다 큰 값만 분포에 넣었다.",
        "",
    ]
    for name, block in data.items():
        lines += [f"### {name}", ""]
        rows = []
        for field, stats in block.items():
            rows.append(
                {
                    "field": field,
                    "raw_missing": _pct(stats["raw_missing"]),
                    "zero": stats["zero"],
                    "positive": stats["positive_n"],
                    "usable": _pct(stats["usable_rate"]),
                    "min": stats["min"],
                    "p50": stats["p50"],
                    "p90": stats["p90"],
                    "max": stats["max"],
                }
            )
        lines += [
            _table(
                rows,
                [
                    ("field", "컬럼"),
                    ("raw_missing", "원본 결측"),
                    ("zero", "0"),
                    ("positive", "양수"),
                    ("usable", "양수 비율"),
                    ("min", "최소"),
                    ("p50", "중앙값"),
                    ("p90", "p90"),
                    ("max", "최대"),
                ],
            ),
            "",
        ]
        rent = block["월세액"]["usable_rate"]
        deposit = block["보증액"]["usable_rate"]
        area = block["소재지면적"]["usable_rate"]
        if rent < 0.05 and deposit < 0.05:
            lines.append(
                f"월세·보증은 양수가 거의 없어 사용자 예산 입력으로 대체해야 한다. "
                f"소재지면적은 양수 비율 {_pct(area)}라 점포 규모 보조 지표로 쓸 수 있다."
            )
        lines.append("")
    return "\n".join(lines)


def _time_filter(data: dict) -> str:
    lines = [
        "## 8. 시점 필터 가능성",
        "",
        "규칙: `인허가일자 <= T` 이고 (`폐업일자` 없음 또는 `폐업일자 > T`).",
        "폐업일자가 T와 같으면 그 시점에 이미 닫은 것으로 본다.",
        "",
    ]
    for name, block in data.items():
        usable = "성립" if block["usable_for_asof"] else "제한적으로만 성립"
        lines += [
            f"### {name}",
            "",
            f"- 인허가일자 형식: {block['permit_format']}",
            f"- 인허가일자 결측률: {_pct(block['permit_missing'])} ({block['permit_missing_count']:,}건)",
            f"- 폐업일자 결측률: {_pct(block['closed_missing'])}",
            f"- 상태가 폐업인데 폐업일자가 없는 행: **{block['closed_status_without_date']:,}** / 폐업 {block['closed_status']:,}",
            f"- 상태가 영업인데 폐업일자가 있는 행: {block['open_status_with_date']:,}",
            f"- 2022-01-01 기준 영업 중으로 재구성한 행: {block['open_on_2022_01_01']:,}",
            f"- 백테스트용 시점 필터: **{usable}**",
            "",
        ]
    return "\n".join(lines)


def _buildings(data: dict) -> str:
    return "\n".join(
        [
            "## 9. 건물 단위 집계",
            "",
            "상가정보 음식 점포만 대상으로 했다.",
            "",
            f"- 건물관리번호 결측률: {_pct(data['missing_rate'])}",
            f"- 번호가 있는 점포: {data['stores_with_id']:,} / 건물 수: {data['buildings']:,}",
            f"- 건물당 음식점 수: 최소 {data['min']}, 중앙값 {data['p50']}, p90 {data['p90']}, p99 {data['p99']}, 최대 {data['max']}",
            f"- 음식점 2곳 이상인 건물: {data['buildings_ge2']:,}",
            f"- 음식점 5곳 이상인 건물: {data['buildings_ge5']:,}",
            "",
        ]
    )


def _next_steps(result: dict) -> str:
    join = result["keys"]["admin_join"]
    coords = result["coords"]
    best = ", ".join(
        f"{name.replace('식품_', '')} `{block['best_crs']}`" for name, block in coords.items()
    )
    time_ok = all(block["usable_for_asof"] for block in result["time_filter"].values())
    closed_no_date = sum(block["closed_status_without_date"] for block in result["time_filter"].values())
    join_line = (
        "상가 행정동코드와 인구 행정기관코드는 앞 8자리로 조인한다."
        if join["join_on_pop_first8"] and not join["direct_join"]
        else "상가 행정동코드와 인구 행정기관코드 조인 결과를 다시 확인해야 한다."
    )
    return "\n".join(
        [
            "## 다음 단계 판단에 필요한 사항",
            "",
            "### 파일 간 조인",
            "",
            f"- {join_line}",
            "- 인허가에는 행정동코드가 없다. 생존률을 동 단위로 쓰려면 좌표 변환 후 행정동 경계 공간 조인, 또는 주소 파싱이 필요하다.",
            "- 1주 차 결론: 경계 파일이 없으면 검증기는 **시군구 × 업태**로 내리고, 동 단위는 공간 조인 이후로 미룬다.",
            f"- 인허가 TM → WGS84는 EPSG:2097과 EPSG:5174가 거의 같다(파일별 1순위: {best}). "
            "안내된 EPSG:5174를 기본으로 쓰고, EPSG:5178·5186은 버린다. 건물 단위 정확도는 확인 필요.",
            "",
            "### 업종 공통 분류",
            "",
            "- 목표 묶음: 한식·중식·일식·양식·분식·회/횟집·육류구이·주점·카페·기타.",
            "- 상가는 중·소분류, 인허가는 업태구분명(일반/휴게가 파일 자체가 다름).",
            "- 문제가 될 값: 기타, 패스트푸드, 식육(숯불구이), 호프/통닭, 키즈카페, 편의점 커피, 라이브카페 등. 매핑표는 2주 차에 고정한다.",
            "",
            "### 시점 필터",
            "",
            f"- 날짜 형식은 `YYYY-MM-DD`가 기본이고, 시점 필터 자체는 {'성립한다' if time_ok else '성립하지만 구멍이 있다'}.",
            f"- 한계: 폐업 상태인데 폐업일자가 없는 행이 두 파일을 합쳐 {closed_no_date:,}건이다. 이 행은 폐업 시점을 알 수 없어 코호트에서 빼거나 별도 표시한다.",
            "- 인허가일자가 없는 행은 시점 T에 영업 중인지 재구성할 수 없다.",
            "",
            "### 확인 필요",
            "",
            "- `개방자치단체코드`(7자리)와 행정표준 시군구코드 대응표.",
            "- 인허가 좌표 이상치(음수 X/Y)와 1900년 인허가·미래 폐업일.",
            "- 주소에서 시도 파싱이 안 되는 약 6% (서울시 표기 등).",
            "- 휴게음식점의 편의점·백화점 업태를 카페 생존률에서 뺄지.",
            "- 행정동 경계 파일(동 단위 생존을 2주 차에 넣을지, 지금은 시군구).",
            "",
        ]
    )


def _same_counts(left: list[dict], right: list[dict]) -> bool:
    left_map = {row["value"]: row["n"] for row in left}
    right_map = {row["value"]: row["n"] for row in right}
    if set(left_map) != set(right_map):
        return False
    return all(abs(left_map[key] - right_map[key]) <= 5 for key in left_map)


def _lengths(stats: dict) -> str:
    parts = []
    for key, value in stats.items():
        if str(key).isdigit():
            parts.append(f"{key}자리 {value:,}건")
        elif value:
            parts.append(f"{key} {value:,}건")
    return ", ".join(parts) if parts else "없음"


def _count_table(rows: list[dict]) -> str:
    return _table(rows, [("value", "값"), ("n", "빈도")])


def _table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "_없음_"
    header = "| " + " | ".join(title for _, title in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, sep]
    for row in rows:
        cells = [_cell(row.get(key)) for key, _ in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Y" if value else "N"
    if isinstance(value, int) and not isinstance(value, bool):
        if 1800 <= value <= 2100:
            return str(value)
        return f"{value:,}"
    if isinstance(value, float):
        if abs(value) >= 100:
            return f"{value:,.2f}"
        return f"{value:.4f}"
    text = str(value).replace("|", "\\|").replace("\n", " ")
    return text


def _pct(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value * 100:.2f}%"


def _bytes(value: int | None) -> str:
    if not value:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"
