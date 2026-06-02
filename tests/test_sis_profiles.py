import pytest
from fris_sis_profiles import get_profile, list_profiles, INTERNAL_FIELDS, SIS_PROFILES


def test_all_profiles_have_required_keys():
    required = {"display_name", "description", "column_map", "level_map",
                "withdrawn_codes", "graduated_true_value"}
    for key, profile in SIS_PROFILES.items():
        assert required <= set(profile.keys()), f"Profile '{key}' missing keys"


def test_all_profiles_map_to_internal_fields():
    # 'level' is derived from the raw level column — present under every profile.
    # 'graduated_ind' and 'enrollment_status' are raw fields converted by ETL logic.
    checked = INTERNAL_FIELDS - {"default_flag"}
    for key, profile in SIS_PROFILES.items():
        mapped = set(profile["column_map"].values())
        for field in checked:
            assert field in mapped, (
                f"Profile '{key}' doesn't map to internal field '{field}'"
            )


def test_get_profile_returns_valid_dict():
    for key in SIS_PROFILES:
        profile = get_profile(key)
        assert profile["display_name"]
        assert isinstance(profile["column_map"], dict)


def test_get_profile_case_insensitive():
    assert get_profile("BANNER") == get_profile("banner")
    assert get_profile("  Banner  ") == get_profile("banner")


def test_get_profile_unknown_key_raises():
    with pytest.raises(ValueError, match="Unknown SIS profile"):
        get_profile("nonexistent_sis")


def test_list_profiles_returns_all_without_column_map():
    profiles = list_profiles()
    assert len(profiles) == len(SIS_PROFILES)
    for p in profiles:
        assert "key" in p
        assert "display_name" in p
        assert "expected_columns" in p
        assert "column_map" not in p  # must not expose internal mapping to UI


def test_level_maps_produce_only_canonical_values():
    canonical = {"UG", "GR"}
    for key, profile in SIS_PROFILES.items():
        for raw, mapped in profile["level_map"].items():
            assert mapped in canonical, (
                f"Profile '{key}' maps level '{raw}' → '{mapped}', "
                f"expected one of {canonical}"
            )


def test_servicer_columns_present_in_all_profiles():
    servicer_internals = {"days_delinquent", "num_loans", "original_loan_amount",
                          "current_balance", "payment_plan"}
    for key, profile in SIS_PROFILES.items():
        mapped = set(profile["column_map"].values())
        assert servicer_internals <= mapped, (
            f"Profile '{key}' missing servicer columns: {servicer_internals - mapped}"
        )
