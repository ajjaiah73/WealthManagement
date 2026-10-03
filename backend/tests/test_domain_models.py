from app.domain.client import ClientProfile, FieldStatus, build_fact_find


def test_client_profile_defaults_and_full_name() -> None:
    profile = ClientProfile(client_id="C-TEST", first_name="Test", last_name="User")
    assert profile.age is None
    assert profile.full_name == "Test User"


def test_build_fact_find_marks_missing_fields_explicitly() -> None:
    profile = ClientProfile(client_id="C-TEST", first_name="Test", last_name="User", age=40)
    fact_find = build_fact_find(profile)

    missing = fact_find.missing_fields
    assert "risk_tolerance" in missing
    assert "target_retirement_age" in missing

    age_field = next(f for f in fact_find.fields if f.field == "age")
    assert age_field.status == FieldStatus.PRESENT
    assert age_field.value == 40

    missing_field = next(f for f in fact_find.fields if f.field == "risk_tolerance")
    assert missing_field.value is None
    assert missing_field.status == FieldStatus.MISSING


def test_fact_find_completion_percentage() -> None:
    profile = ClientProfile(client_id="C-TEST", first_name="Test", last_name="User")
    fact_find = build_fact_find(profile)
    # concessional/non-concessional contributions default to 0.0, which is a real
    # present value (zero contributions), not missing information - so 2 of the
    # 12 required fields are present out of the box.
    assert fact_find.completion_percentage == round(2 / 12 * 100, 1)
