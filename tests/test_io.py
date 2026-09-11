from pathlib import Path

import pytest

from src.eda.io import detect_encoding, read_csv_header


def test_detect_encoding_prefers_cp949_for_euc_kr_bytes(tmp_path: Path) -> None:
    path = tmp_path / "license.csv"
    path.write_bytes("업태구분명,사업장명\n한식,원푸드\n".encode("cp949"))

    assert detect_encoding(path) == "cp949"


def test_detect_encoding_reads_utf8_sig(tmp_path: Path) -> None:
    path = tmp_path / "sanga.csv"
    path.write_bytes("\ufeff상권업종대분류명,행정동코드\n음식,11200660\n".encode("utf-8-sig"))

    assert detect_encoding(path) == "utf-8-sig"


def test_detect_encoding_raises_when_undecodable(tmp_path: Path) -> None:
    path = tmp_path / "broken.csv"
    path.write_bytes(b"\xff\xfe\x00\x00")

    with pytest.raises(ValueError, match="인코딩"):
        detect_encoding(path)


def test_read_csv_header_strips_quotes(tmp_path: Path) -> None:
    path = tmp_path / "quoted.csv"
    path.write_text('"상가업소번호","상호명"\n"1","가게"\n', encoding="utf-8")

    assert read_csv_header(path, encoding="utf-8") == ["상가업소번호", "상호명"]
