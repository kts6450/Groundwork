# 외식 창업 기획 도우미 (가칭)

공공데이터로 상권을 분석하고, 예비 외식 창업자에게 업종 → 입지 → 컨셉·메뉴 → 브랜드명·로고까지 한 번에 제안하는 SaaS 웹 서비스.
개업 이후에는 저장된 프로젝트를 새 시점으로 다시 계산해 상권 변화를 알리고 브랜드 자산을 만들어 준다.

## 구조

- `src/` — 분석·생성 로직 (Python). 화면·API를 모른다
- `api/` — FastAPI. `src/`를 엔드포인트로 노출
- `web/` — Next.js 검증 화면 (제품명 남음). 지도는 나중에
- 인증·DB는 Supabase, LLM은 Claude API

## 실행 방법

### 1. 가상환경 (Windows PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

### 2. 데이터

공공데이터포털(data.go.kr)에서 받은 원본 파일을 `data/raw/`에 그대로 넣는다. 원본은 수정·삭제하지 않는다.
필요한 파일 목록은 `CLAUDE.md`의 "데이터" 절 참고.

### 3. 데이터 파이프라인

프로젝트 루트에서 순서대로:

```powershell
python -m src.eda                    # 원본 → parquet, reports/eda.md
python -m src.scoring.run_survival   # 생존표, reports/survival.md + categories.md
python -m src.scoring.run_backtest   # 백테스트, reports/backtest.md
python -m src.monitor.run_timeline   # 개·폐업 집계 (5단계용)
```

업종 매핑을 바꾸면 `run_survival` → `run_backtest` 순서로 다시 돌린다.

### 4. 서버 (터미널 두 개)

```powershell
python -m uvicorn api.main:app --port 8000
cd web; npm install; npm run dev      # http://localhost:3000
```

`.env.example`을 `.env`로 복사하고 `ANTHROPIC_API_KEY`를 넣으면 2·3단계가 LLM으로 생성된다.
키가 없어도 규칙 기반 목업으로 화면은 그대로 뜬다.

### 5. 테스트

```powershell
python -m pytest -q
```

### 4. 생존표·검증

```powershell
python -m src.scoring
python -m src.scoring.verify "서울특별시 종로구 대학로11길 22" "커피숍"
```

생존표는 `reports/survival.md`, 업종 매핑은 `reports/categories.md`다.

### 5. 검증 화면

터미널 두 개. 가상환경은 루트에서.

```powershell
uvicorn api.main:app --reload --port 8000
```

```powershell
cd web
npm install
npm run dev
```

브라우저에서 `http://localhost:3000`. `/backend/*`는 Next가 FastAPI로 넘긴다.

## 문서

- `종합프로젝트 초안.md` — 기획 원문. 차별점·아키텍처·일정·로드맵·EDA 항목
- `CLAUDE.md` — 프로젝트 개요·폴더 구조·작업 규칙 (요약)
- `docs/interfaces.md` — 단계 간 입출력(JSON) 정의
- `docs/interfaces.md` — 단계 간 입출력(JSON) 정의
- `docs/decisions.md` — 결정 기록 (무엇을 왜 택했고 무엇을 기각했는지)
- `reports/` — eda.md, categories.md, survival.md, backtest.md
- `docs/market.md` — 경쟁 서비스·사업화 검토
