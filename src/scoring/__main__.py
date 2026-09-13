"""python -m src.scoring  → 생존표 재계산
python -m src.scoring.verify "주소" "업태"  → 한 건 검증
"""

from src.scoring.run_survival import main

if __name__ == "__main__":
    main()
