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


def test_parse_sido_sgg_keeps_real_general_gu() -> None:
    assert parse_sido_sgg("경기도 성남시 분당구 정자로 1") == ("경기도", "성남시 분당구")
    assert parse_sido_sgg("경기도 화성시 동탄구 동탄대로5길 21") == ("경기도", "화성시 동탄구")


def test_parse_sido_sgg_drops_false_gu_suffix() -> None:
    assert parse_sido_sgg("충청남도 공주시 유구읍 유구마곡사로 12") == ("충청남도", "공주시")
    assert parse_sido_sgg("강원특별자치도 원주시 행구동 1") == ("강원특별자치도", "원주시")
    assert parse_sido_sgg("전라남도 목포시 용해지구 1") == ("전라남도", "목포시")


def test_parse_sido_sgg_jeonnam_gwangju_splits_to_old_sido() -> None:
    assert parse_sido_sgg("전남광주통합특별시 북구 하서로 200") == ("광주광역시", "북구")
    assert parse_sido_sgg("전남광주통합특별시 광산구 첨단중앙로 1") == ("광주광역시", "광산구")
    assert parse_sido_sgg("전남광주통합특별시 목포시 영산로 12") == ("전라남도", "목포시")
    assert parse_sido_sgg("전남광주통합특별시 여수시 시청로 1") == ("전라남도", "여수시")


def test_parse_sido_sgg_series_matches_scalar() -> None:
    import pandas as pd

    from src.eda.coords import parse_sido_sgg_series

    addresses = pd.Series(
        [
            "서울특별시 종로구 창경궁로 109",
            "경기도 성남시 분당구 정자로 1",
            "세종특별자치시 한솔동 123",
            "전남광주통합특별시 북구 하서로 200",
            "전남광주통합특별시 목포시 영산로 12",
            "이상한 주소",
            None,
        ]
    )
    out = parse_sido_sgg_series(addresses)

    assert out["sido"].tolist() == [
        "서울특별시",
        "경기도",
        "세종특별자치시",
        "광주광역시",
        "전라남도",
        "",
        "",
    ]
    assert out["sgg"].tolist() == ["종로구", "성남시 분당구", "", "북구", "목포시", "", ""]
