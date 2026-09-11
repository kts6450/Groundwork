from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "reports"

LICENSE_GENERAL_CSV = DATA_RAW / "식품_일반음식점.csv"
LICENSE_REST_CSV = DATA_RAW / "식품_휴게음식점.csv"
POPULATION_CSV = DATA_RAW / "행정안전부_지역별(행정동) 성별 연령별 주민등록 인구수_20260831.csv"
SANGA_DIR = DATA_RAW / "소상공인시장진흥공단_상가(상권)정보_20260630"

LICENSE_GENERAL_PARQUET = DATA_INTERIM / "license_general.parquet"
LICENSE_REST_PARQUET = DATA_INTERIM / "license_rest.parquet"
SANGA_FOOD_PARQUET = DATA_INTERIM / "sanga_food.parquet"
POPULATION_PARQUET = DATA_INTERIM / "population.parquet"
PROFILE_JSON = DATA_INTERIM / "eda_profile.json"
REPORT_MD = REPORTS_DIR / "eda.md"

LICENSE_COLS = [
    "개방자치단체코드",
    "관리번호",
    "인허가일자",
    "영업상태명",
    "폐업일자",
    "소재지면적",
    "사업장명",
    "업태구분명",
    "도로명주소",
    "보증액",
    "상세영업상태명",
    "상세영업상태코드",
    "영업상태코드",
    "월세액",
    "위생업태명",
    "좌표정보(X)",
    "좌표정보(Y)",
    "지번주소",
]

SANGA_COLS = [
    "상호명",
    "상권업종대분류명",
    "상권업종중분류명",
    "상권업종소분류명",
    "시도명",
    "시군구코드",
    "시군구명",
    "행정동코드",
    "행정동명",
    "법정동코드",
    "법정동명",
    "지번주소",
    "도로명주소",
    "건물관리번호",
    "층정보",
    "경도",
    "위도",
]

POP_COLS = [
    "행정기관코드",
    "기준연월",
    "시도명",
    "시군구명",
    "읍면동명",
    "계",
    "남자",
    "여자",
]
