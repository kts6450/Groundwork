# 단계 간 인터페이스 정의

각 단계는 아래에 정의한 JSON 형식만 주고받는다. 앞 단계의 출력이 다음 단계의 입력이다.
분석·생성 로직(`src/`)은 이 형식만 알고, FastAPI(`api/`)와 Next.js(`web/`)는 이 형식을 그대로 전달한다.

**구현 상태**: 1단계(검증)는 동작한다. 2·3단계는 형식만 정의돼 있고 구현 중이다. 6·7단계는 아직 없다.

## 0. 공통 규칙

- 인코딩은 UTF-8, 키는 `snake_case` 영문.
- 비율은 0~1 사이 소수로 주고받는다. `%`로 바꾸는 것은 화면의 몫이다.
- 날짜는 `YYYY-MM-DD`, 기간은 `from`/`to` 쌍.
- 금액은 원 단위 정수.
- 실패는 예외가 아니라 `{"error": "<코드>", "reason": "<사람이 읽는 한 문장>"}`로 돌려준다.
  현재 쓰는 코드: `unmapped`(매핑표에 없는 업태), `excluded`(검증 대상이 아닌 업태), `no_national_rate`.
- 생성 단계(2·3)는 LLM 키가 없어도 규칙 기반 목업을 같은 형식으로 돌려준다. 그 경우 `"source": "mock"`.

## 1. 사용자 조건 (파이프라인 입력)

```json
{
  "address": "서울특별시 마포구 양화로 100",
  "business_type": "커피숍",
  "budget_krw": 80000000,
  "experience": "none",
  "preferences": ["조용한 분위기", "혼자 운영"]
}
```

| 항목 | 쓰이는 단계 | 비고 |
|---|---|---|
| `address` | 2 (검증) | 시도·시군구만 쓴다. 상세 주소는 현재 쓰지 않음 |
| `business_type` | 2 (검증) | 인허가 업태구분명. 목록은 `/catalog`가 준다 |
| `budget_krw` | 3 (컨셉) | 월세·보증금 데이터가 98% 비어 있어(EDA) 상권 분석에는 못 쓴다. 가격대·규모 제안에만 |
| `experience` | 3 (컨셉) | `none` / `some` / `experienced`. 프롬프트에만 들어감 |
| `preferences` | 3 (컨셉), 4 (브랜딩) | 자유 문장 배열. 선택 |

`address`와 `business_type`만 필수다. 나머지가 없으면 2단계는 그대로 돌고, 3단계는 기본값으로 생성한다.

## 2. 입지·업종 검증 (1단계, 구현됨)

`src/scoring/verify.py` → `POST /backend/verify`

### 입력

```json
{ "address": "서울특별시 마포구 양화로 100", "business_type": "커피숍" }
```

### 출력

```json
{
  "sido": "서울특별시",
  "sgg": "마포구",
  "business_type": "커피숍",
  "category": "카페",
  "level": "시군구",
  "n": 1499,
  "surv_1y": 0.8825883922615076,
  "surv_3y": 0.57104736490994,
  "nation_3y": 0.6460747095268615,
  "diff_3y": -0.07502734461692151,
  "grade": "위험",
  "reason": "서울특별시 마포구 카페는 3년 생존 57.1%로 전국(64.6%)보다 낮다. 시군구 표본 1,499곳.",
  "evidence": "2020~2022년에 개업한 점포로 확인해 보면, 같은 '위험' 판정을 받은 50,722곳의 3년 생존은 59.6%였다."
}
```

- `category`: 13개 공통 묶음 중 하나 (`src/scoring/categories.py`)
- `level`: 실제로 답한 표의 수준. `시군구` → `시도` → `전국` 순으로 내려간다
- `n`: 그 칸의 표본 수. 10 미만이면 그 칸을 만들지 않고 한 단계 내려간다
- `grade`: `diff_3y`가 +0.05 이상 `합격`, -0.05 이하 `위험`, 사이는 `주의`
- `evidence`: 백테스트에서 나온 같은 등급의 실제 성적. 백테스트를 돌리지 않았으면 빈 문자열

### 참고: 업태 목록과 전국 생존률

`GET /backend/catalog`

```json
{
  "business_types": [{ "business_type": "냉면집", "category": "한식" }],
  "nation": [{ "category": "고기구이", "n": 25862, "surv_1y": 0.9376, "surv_3y": 0.7647 }]
}
```

## 3. 컨셉·메뉴·가격대 (2단계)

`src/concept/` → `POST /backend/concept` (구현 중)

### 입력

1단계 출력에 사용자 조건을 더한 것. 검증 결과를 그대로 넘겨 근거로 쓴다.

```json
{
  "verdict": { "…1단계 출력 전체…" },
  "budget_krw": 80000000,
  "experience": "none",
  "preferences": ["조용한 분위기"]
}
```

### 출력

```json
{
  "source": "llm",
  "concept": {
    "one_liner": "혼자 운영하는 조용한 로스터리",
    "target": "인근 사무실 30대 직장인",
    "differentiator": "마포구 카페 3년 생존이 전국보다 낮아, 회전율 대신 단골에 건다",
    "tone": ["차분한", "정제된"]
  },
  "menu": [
    { "name": "드립 커피", "price_krw": 5500, "role": "signature" },
    { "name": "플랫 화이트", "price_krw": 5000, "role": "core" }
  ],
  "price_band": { "low_krw": 4500, "high_krw": 9000, "average_krw": 6200 },
  "grounds": ["마포구 카페 3년 생존 57.1%", "전국 카페 64.6%"]
}
```

- `source`: `llm` 또는 `mock`(키 없이 규칙 기반으로 만든 경우)
- `menu[].role`: `signature`(대표) / `core`(주력) / `side`(보조)
- `grounds`: 1단계 숫자에서 그대로 가져온 근거 문장. LLM이 지어내면 안 되는 값

## 4. 브랜드명·로고 (3단계)

`src/branding/` → `POST /backend/brand` (아직 없음)

### 입력

```json
{ "concept": { "…2단계 출력…" }, "category": "카페", "preferences": ["한글 이름"] }
```

### 출력

```json
{
  "source": "llm",
  "names": [{ "name": "머무름", "reason": "오래 앉아 있는 카페라는 컨셉", "risk": "동명 상표 확인 필요" }],
  "palette": { "primary": "#1c6b4a", "secondary": "#c4841d", "background": "#f3ead7" },
  "logo_svg": "<svg viewBox=\"0 0 120 120\">…</svg>"
}
```

- 로고는 이미지 모델이 아니라 LLM이 SVG 문자열을 직접 생성한다(비용·의존성 감소, `docs/decisions.md`)
- `names[].risk`: 상표 확인은 사람이 해야 한다는 표시. 자동 조회는 하지 않는다

## 5. 결과 화면 (4단계)

### 입력

2·3단계 출력과 1단계 검증 결과를 그대로 받는다. 화면은 계산하지 않고 표시만 한다.

```json
{ "verdict": {}, "concept": {}, "brand": {} }
```

현재 화면은 1단계 검증 결과만 표시한다. 지도와 업종 분포도는 아직 없다.

## 6. 사용자 프로젝트 (저장 객체)

4단계 결과를 한 덩어리로 저장한다. 7단계(개업 이후)의 입력이다. **아직 구현하지 않았다.**

### 스키마

```json
{
  "project_id": "uuid",
  "user_id": "uuid",
  "created_at": "2026-09-13",
  "computed_at": "2026-09-13",
  "location": { "address": "…", "sido": "서울특별시", "sgg": "마포구" },
  "category": "카페",
  "business_type": "커피숍",
  "verdict": { "…1단계 출력…" },
  "concept": { "…2단계 출력…" },
  "brand": { "…3단계 출력…" }
}
```

`computed_at`이 중요하다. 7단계는 이 시점과 새 시점의 생존표를 비교한다.

## 7. 개업 이후 (5단계)

### 7-1. 상권 변화 알림

#### 입력 (사용자 프로젝트 + 새 시점)

```json
{ "project_id": "uuid", "as_of": "2027-03-01" }
```

#### 출력

```json
{
  "from": "2026-09-13",
  "to": "2027-03-01",
  "same_category_opened": 4,
  "same_category_closed": 2,
  "surv_3y_then": 0.571,
  "surv_3y_now": 0.559,
  "grade_then": "위험",
  "grade_now": "위험",
  "message": "마포구 카페가 같은 기간 4곳 열고 2곳 닫았다."
}
```

시점 필터(`src/eda/history.py`의 `open_at`)가 이 비교의 기반이다. 같은 함수가 백테스트에도 쓰인다.

### 7-2. 브랜드 자산 생성

#### 입력 (사용자 프로젝트 + 요청 종류)

```json
{ "project_id": "uuid", "asset": "seasonal_menu", "context": "겨울 신메뉴 2종" }
```

`asset`: `seasonal_menu` / `sns_post` / `event_banner`

#### 출력

```json
{ "source": "llm", "asset": "seasonal_menu", "title": "겨울 한정", "body": "…", "svg": "<svg>…</svg>" }
```

저장된 브랜드 정체성(6번의 `brand`)을 프롬프트에 그대로 넣어 톤을 유지한다.
