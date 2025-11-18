from backend.app.utils.country_normalization import normalize_country_code


def test_normalize_country_accepts_iso_codes() -> None:
    assert normalize_country_code("de") == "DE"
    assert normalize_country_code("DEU") == "DEU"


def test_normalize_country_handles_known_names() -> None:
    assert normalize_country_code("Deutschland") == "DE"
    assert normalize_country_code("  germany  ") == "DE"
    assert normalize_country_code("Österreich") == "AT"


def test_normalize_country_returns_none_for_unknown_values() -> None:
    assert normalize_country_code("Planet Express") is None
    assert normalize_country_code("") is None
    assert normalize_country_code(None) is None
