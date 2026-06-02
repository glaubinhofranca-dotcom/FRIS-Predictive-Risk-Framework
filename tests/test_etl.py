import pandas as pd
import pytest
from fris_etl import _apply_sis_profile
from fris_utils import clean_currency
from fris_config import DEFAULT_DAYS_THRESHOLD
from fris_sis_profiles import get_profile


def _banner_df(**overrides) -> pd.DataFrame:
    """Minimal valid Banner-format DataFrame with two students."""
    row = {
        "ID": ["U001", "U002"],
        "LEVL_CODE": ["UG", "GR"],
        "PROGRAM": ["CS", "MBA"],
        "MAJR_DESC": ["Computer Science", "Business"],
        "STYP_DESC": ["New", "Transfer"],
        "CAMP_CODE": ["MAIN", "ONLINE"],
        "OVERALL_LGPA_GPA": [3.5, 2.8],
        "OVERALL_LGPA_HOURS_EARNED": [60, 30],
        "GRADUATED_IND": ["Y", "N"],
        "SFBETRM_ESTS_CODE": ["EE", "WD"],
        "Days Delinquent": [0, 300],
        "# of Loans": [1, 2],
        "Original Loan Amount": ["$10,000", "$20,000"],
        "Current Principal Balance": ["$8,000", "$20,000"],
        "Payment Plan": ["Standard", "IBR"],
    }
    row.update(overrides)
    return pd.DataFrame(row)


# ── clean_currency ─────────────────────────────────────────────────────────────

def test_clean_currency_typical_values():
    s = pd.Series(["$1,234.56", "$0.00", "500"])
    result = clean_currency(s)
    assert result[0] == pytest.approx(1234.56)
    assert result[1] == pytest.approx(0.0)
    assert result[2] == pytest.approx(500.0)


def test_clean_currency_non_numeric_becomes_nan():
    s = pd.Series(["N/A", "unknown"])
    result = clean_currency(s)
    assert all(pd.isna(result))


# ── _apply_sis_profile ─────────────────────────────────────────────────────────

def test_apply_banner_profile_renames_columns():
    df = _banner_df()
    result = _apply_sis_profile(df, get_profile("banner"))
    assert "student_id" in result.columns
    assert "level" in result.columns
    assert "gpa" in result.columns
    assert "ID" not in result.columns
    assert "LEVL_CODE" not in result.columns


def test_apply_banner_profile_preserves_level_values():
    df = _banner_df()
    result = _apply_sis_profile(df, get_profile("banner"))
    assert set(result["level"]) == {"UG", "GR"}


def test_apply_peoplesoft_profile_normalizes_ugrd_to_ug():
    profile = get_profile("peoplesoft")
    df = pd.DataFrame({
        "EMPLID": ["P001"],
        "ACAD_LEVEL_BOT": ["UGRD"],
        "ACAD_PROG": ["BSCS"],
        "ACAD_PLAN": ["CS"],
        "ADMIT_TYPE": ["FTF"],
        "CAMPUS": ["MAIN"],
        "CUM_GPA": [3.0],
        "TOT_TAKEN_GPA": [45],
        "COMPLETION_STAT": ["CM"],
        "STDNT_ENRL_STATUS": ["ACTV"],
        "Days Delinquent": [0],
        "# of Loans": [1],
        "Original Loan Amount": ["$5,000"],
        "Current Principal Balance": ["$4,000"],
        "Payment Plan": ["Standard"],
    })
    result = _apply_sis_profile(df, profile)
    assert result["level"].iloc[0] == "UG"


def test_apply_profile_case_insensitive_column_match():
    df = _banner_df()
    # Lowercase all column names — ETL should still match them
    df.columns = [c.lower() for c in df.columns]
    result = _apply_sis_profile(df, get_profile("banner"))
    assert "student_id" in result.columns


def test_apply_profile_missing_columns_raises():
    profile = get_profile("banner")
    df = pd.DataFrame({"ID": ["U001"], "LEVL_CODE": ["UG"]})
    with pytest.raises(ValueError, match="missing"):
        _apply_sis_profile(df, profile)


# ── default flag threshold ─────────────────────────────────────────────────────

def test_default_flag_boundary():
    """Only days > DEFAULT_DAYS_THRESHOLD should be flagged."""
    days = pd.to_numeric(
        pd.Series([DEFAULT_DAYS_THRESHOLD - 1, DEFAULT_DAYS_THRESHOLD,
                   DEFAULT_DAYS_THRESHOLD + 1, 0]),
        errors="coerce",
    ).fillna(0)
    flags = (days > DEFAULT_DAYS_THRESHOLD).astype(int)
    assert list(flags) == [0, 0, 1, 0]


def test_default_days_threshold_value():
    """Threshold is 270 per 34 CFR § 682.200."""
    assert DEFAULT_DAYS_THRESHOLD == 270
