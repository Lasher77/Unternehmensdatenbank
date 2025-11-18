from backend.app.schemas.company import Company


def test_company_normalizes_invalid_terminated_string() -> None:
    company = Company(source_id="acme", terminated="n/a")
    assert company.terminated is None


def test_company_parses_truthy_strings() -> None:
    company = Company(source_id="acme", terminated="YES")
    assert company.terminated is True


def test_company_parses_falsey_numbers() -> None:
    company = Company(source_id="acme", terminated=0)
    assert company.terminated is False


def test_company_preserves_boolean_value() -> None:
    company = Company(source_id="acme", terminated=False)
    assert company.terminated is False


def test_company_handles_whitespace_string() -> None:
    company = Company(source_id="acme", terminated="   ")
    assert company.terminated is None


def test_company_normalizes_country_fields() -> None:
    company = Company(
        source_id="acme",
        country=" deutschland ",
        register_country="germany",
    )

    assert company.country == "DE"
    assert company.register_country == "DE"


def test_company_ignores_unknown_country_value() -> None:
    company = Company(source_id="acme", country="Planet Express")
    assert company.country is None
