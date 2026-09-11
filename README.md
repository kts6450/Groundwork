# 외식 창업 기획 도우미 (가칭)

공공데이터로 상권을 분석하고, 예비 외식 창업자에게 업종 → 입지 → 컨셉·메뉴 → 브랜드명·로고까지 한 번에 제안하는 서비스.

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

```powershell
python -m src.eda.<스크립트명>
```

결과는 `reports/eda.md`에 정리한다.

## 문서

- `CLAUDE.md` — 프로젝트 개요·폴더 구조·작업 규칙
- `docs/interfaces.md` — 단계 간 입출력(JSON) 정의
- `종합프로젝트 초안.md` — 원본 기획 초안
