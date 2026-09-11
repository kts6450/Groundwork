from src.eda.coords import parse_sido_sgg, transform_xy, within_korea


def test_parse_sido_sgg_seoul_gu() -> None:
    assert parse_sido_sgg("서울특별시 종로구 창경궁로 109") == ("서울특별시", "종로구")


def test_parse_sido_sgg_gyeonggi_general_gu() -> None:
    assert parse_sido_sgg("경기도 성남시 분당구 정자로 1") == ("경기도", "성남시 분당구")


def test_parse_sido_sgg_sejong_has_no_sgg() -> None:
    assert parse_sido_sgg("세종특별자치시 한솔동 123") == ("세종특별자치시", "")


def test_transform_xy_5174_puts_myeongnyun_in_seoul() -> None:
    lon, lat = transform_xy(199968.850339263, 453338.316074117, "EPSG:5174")

    assert 126.9 < lon < 127.1
    assert 37.5 < lat < 37.7
    assert within_korea(lon, lat) is True


def test_within_korea_rejects_outliers() -> None:
    assert within_korea(0.0, 0.0) is False
