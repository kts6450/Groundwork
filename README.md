# 외식 창업 기획 도우미 (가칭)

공공데이터로 상권을 분석하고, 예비 외식 창업자에게 업종 → 입지 → 컨셉·메뉴 → 브랜드명·로고까지 한 번에 제안하는 SaaS 웹 서비스.
개업 이후에는 저장된 프로젝트를 새 시점으로 다시 계산해 상권 변화를 알리고 브랜드 자산을 만들어 준다.

## 구조

- `src/` — 분석·생성 로직 (Python). 화면·API를 모른다
- `api/` — FastAPI. `src/`를 엔드포인트로 노출 (8주차부터)
- `web/` — Next.js + Kakao Maps (8주차부터)
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

### 3. EDA

프로젝트 루트에서:

```powershell
python -m src.eda
```

원본만 다시 parquet로 바꿀 때는 `python -m src.eda.convert`, 항목별 재계산과 보고서는 `python -m src.eda.run_all`이다. 결과는 `reports/eda.md`다.

## 문서

- `종합프로젝트 초안.md` — 기획 원문. 차별점·아키텍처·일정·로드맵·EDA 항목
- `CLAUDE.md` — 프로젝트 개요·폴더 구조·작업 규칙 (요약)
- `docs/interfaces.md` — 단계 간 입출력(JSON) 정의
- `docs/decisions.md` — 결정 기록 (무엇을 왜 택했고 무엇을 기각했는지)
- `docs/market.md` — 경쟁 서비스·사업화 검토
