"""
FRIS — SIS Profile Definitions

Each profile maps a Student Information System's export column names to
the internal canonical names used throughout the pipeline. The ETL applies
the profile immediately after loading the file, so all downstream code
(EDA, segmentation, model) works exclusively with internal names.

IMPORTANT: Column names for non-Banner SIS systems are representative of
typical report exports. Validate against actual exports before production use.
"""

from __future__ import annotations

# Internal field names that the pipeline expects after profile application.
# These are the only names EDA / segmentation / model ever see.
INTERNAL_FIELDS = {
    "student_id",
    "level",           # normalized to "UG" or "GR"
    "program",
    "major",
    "student_type",
    "campus_code",
    "gpa",
    "credits_earned",
    "num_loans",
    "original_loan_amount",
    "current_balance",
    "payment_plan",
    "graduated_ind",   # raw value — converted to 0/1 by ETL using graduated_true_value
    "enrollment_status",  # raw status code — converted to withdrawn 0/1 using withdrawn_codes
    "days_delinquent",
}

# Loan servicer columns are the same across all SIS profiles.
_SERVICER_COLUMNS: dict[str, str] = {
    "Days Delinquent":           "days_delinquent",
    "# of Loans":                "num_loans",
    "Original Loan Amount":      "original_loan_amount",
    "Current Principal Balance": "current_balance",
    "Payment Plan":              "payment_plan",
}

SIS_PROFILES: dict[str, dict] = {

    # ── Banner / Ellucian ─────────────────────────────────────────────────────
    # Used by ~1,200 US institutions. NEC's production SIS.
    "banner": {
        "display_name": "Banner / Ellucian",
        "description": "Used by ~1,200 US institutions. Default for New England College.",
        "column_map": {
            "ID":                        "student_id",
            "LEVL_CODE":                 "level",
            "PROGRAM":                   "program",
            "MAJR_DESC":                 "major",
            "STYP_DESC":                 "student_type",
            "CAMP_CODE":                 "campus_code",
            "OVERALL_LGPA_GPA":          "gpa",
            "OVERALL_LGPA_HOURS_EARNED": "credits_earned",
            "GRADUATED_IND":             "graduated_ind",
            "SFBETRM_ESTS_CODE":         "enrollment_status",
            **_SERVICER_COLUMNS,
        },
        # level_map keys must be UPPERCASE (ETL upcases before lookup)
        "level_map": {"UG": "UG", "GR": "GR"},
        "withdrawn_codes": {"WD", "W4", "W6", "W7"},
        "graduated_true_value": "Y",
    },

    # ── Workday Student ───────────────────────────────────────────────────────
    # Growing adoption among mid-to-large universities.
    # Column names reflect typical Workday Student report builder exports.
    "workday": {
        "display_name": "Workday Student",
        "description": "Used by many large universities. Column names from Workday report builder.",
        "column_map": {
            "Student ID":       "student_id",
            "Academic Level":   "level",
            "Academic Program": "program",
            "Field of Study":   "major",
            "Student Type":     "student_type",
            "Campus":           "campus_code",
            "Cumulative GPA":   "gpa",
            "Credits Earned":   "credits_earned",
            "Degree Conferred": "graduated_ind",
            "Student Status":   "enrollment_status",
            **_SERVICER_COLUMNS,
        },
        "level_map": {
            "UNDERGRADUATE": "UG",
            "GRADUATE":      "GR",
            "UG":            "UG",
            "GR":            "GR",
        },
        "withdrawn_codes": {"WITHDRAWN", "WD", "INACTIVE", "DROPPED"},
        "graduated_true_value": "Y",
    },

    # ── PeopleSoft Campus Solutions (Oracle) ──────────────────────────────────
    # Widely used by large public universities and state systems.
    # Column names reflect typical PS Query / SQR report exports.
    "peoplesoft": {
        "display_name": "PeopleSoft / Oracle",
        "description": "Used by large public universities. Column names from PS Query exports.",
        "column_map": {
            "EMPLID":             "student_id",
            "ACAD_LEVEL_BOT":     "level",
            "ACAD_PROG":          "program",
            "ACAD_PLAN":          "major",
            "ADMIT_TYPE":         "student_type",
            "CAMPUS":             "campus_code",
            "CUM_GPA":            "gpa",
            "TOT_TAKEN_GPA":      "credits_earned",
            "COMPLETION_STAT":    "graduated_ind",
            "STDNT_ENRL_STATUS":  "enrollment_status",
            **_SERVICER_COLUMNS,
        },
        "level_map": {
            "UGRD": "UG",
            "GRAD": "GR",
            "UG":   "UG",
            "GR":   "GR",
        },
        "withdrawn_codes": {"W", "WD", "WDRW", "DISC"},
        "graduated_true_value": "CM",  # "CM" = Complete in PeopleSoft
    },

    # ── Colleague / Ellucian ──────────────────────────────────────────────────
    # Another Ellucian product used by ~700 US institutions.
    # Column names reflect typical Colleague / Ethos API exports.
    "colleague": {
        "display_name": "Colleague / Ellucian",
        "description": "Used by ~700 US institutions. Another Ellucian product (not Banner).",
        "column_map": {
            "ID":               "student_id",
            "STU.ACAD.LEVEL":   "level",
            "ACAD.PROGRAM":     "program",
            "ACAD.MAJORS":      "major",
            "STUDENT.TYPE":     "student_type",
            "LOCATION":         "campus_code",
            "GPA":              "gpa",
            "CREDITS":          "credits_earned",
            "GRADUATION.IND":   "graduated_ind",
            "ACAD.STANDING":    "enrollment_status",
            **_SERVICER_COLUMNS,
        },
        "level_map": {"UG": "UG", "GR": "GR"},
        "withdrawn_codes": {"W", "WD", "WA", "WX"},
        "graduated_true_value": "Y",
    },
}


def get_profile(key: str) -> dict:
    """Return the profile for *key*, raising ValueError if not found."""
    key = key.strip().lower()
    if key not in SIS_PROFILES:
        valid = ", ".join(sorted(SIS_PROFILES))
        raise ValueError(
            f"Unknown SIS profile '{key}'. Valid options: {valid}"
        )
    return SIS_PROFILES[key]


def list_profiles() -> list[dict]:
    """Return UI-friendly list of all profiles (key + metadata, no column_map)."""
    return [
        {
            "key":          k,
            "display_name": v["display_name"],
            "description":  v["description"],
            "expected_columns": list(v["column_map"].keys()),
        }
        for k, v in SIS_PROFILES.items()
    ]
