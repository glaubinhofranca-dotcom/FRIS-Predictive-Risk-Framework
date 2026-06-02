"""
FRIS v3 — ETL Pipeline
New England College · Student Financial Services

CHANGE FROM v2:
    Academic level is now determined exclusively by LEVL_CODE (Banner authoritative field).
    The previous version used the student ID prefix (UG/GR) to filter and classify
    students, which was a proxy. LEVL_CODE is the canonical source in Banner/Ellucian.

CHANGE FROM v3.0:
    Multi-SIS support via fris_sis_profiles.py. Each SIS profile defines the column
    mapping from the source file to internal canonical names. The rest of the pipeline
    works exclusively with internal names and is SIS-agnostic.

PRIMARY SOURCE: Borrower Details.xlsx (or equivalent export from any supported SIS)
    Consolidated by institution IT from SIS + loan servicer exports.
    Already deduplicated at the student level.

OUTPUT: dataset_fris.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

from fris_config import DEFAULT_DAYS_THRESHOLD, BAR_SCALE
from fris_sis_profiles import get_profile
from fris_utils import clean_currency, normalize_str, normalize_str_upper, to_numeric

SCRIPT_DIR = Path(__file__).parent

# Canonical levels after profile normalization
_CANONICAL_LEVELS = {"UG", "GR"}

# Re-export clean_currency so existing call sites keep working
__all__ = ["run_etl", "clean_currency"]


def _load_file(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, **kwargs)
    return pd.read_csv(path, low_memory=False, **kwargs)


def _apply_sis_profile(data: pd.DataFrame, profile: dict) -> pd.DataFrame:
    """
    Rename SIS-specific column names to internal canonical names.

    Steps:
    1. Strip whitespace from all column names in the uploaded file.
    2. Case-insensitive match each expected SIS column.
    3. Rename matched columns to internal names.
    4. Normalize level values via profile["level_map"] (e.g. "UGRD" → "UG").
    5. Raise ValueError listing missing SIS columns if any are not found.
    """
    data.columns = [str(c).strip() for c in data.columns]

    # Build case-insensitive lookup: lowercase → actual name in the uploaded file
    col_lookup: dict[str, str] = {c.lower(): c for c in data.columns}

    column_map: dict[str, str] = profile["column_map"]
    rename_map: dict[str, str] = {}
    missing: list[str] = []

    for sis_col, internal_name in column_map.items():
        if sis_col in data.columns:
            rename_map[sis_col] = internal_name
        else:
            match = col_lookup.get(sis_col.lower())
            if match:
                rename_map[match] = internal_name  # fix casing silently
            else:
                missing.append(f"  • {sis_col}")

    if missing:
        sis_name = profile["display_name"]
        missing_block = "\n".join(missing)
        raise ValueError(
            f"The uploaded file is missing {len(missing)} column(s) expected for {sis_name}.\n\n"
            f"Missing columns:\n{missing_block}\n\n"
            f"Please verify your file matches the {sis_name} export format and re-upload."
        )

    data = data.rename(columns=rename_map)

    # Normalize level to canonical UG / GR using the profile's level_map
    level_map: dict[str, str] = profile["level_map"]
    data["level"] = (
        normalize_str_upper(data["level"])
        .map(lambda v: level_map.get(v, v))
    )

    return data


def run_etl(input_path: Path, session_dir: Path, sis_profile: str = "banner") -> dict:
    """
    Run the full ETL pipeline.

    Parameters
    ----------
    input_path : Path
        Path to the raw borrower data file (.xlsx or .csv).
    session_dir : Path
        Directory where dataset_fris.csv will be written.
    sis_profile : str
        Key of the SIS profile to use (see fris_sis_profiles.py). Default: "banner".

    Returns
    -------
    dict
        Pipeline metrics for the API / dashboard.
    """
    session_dir = Path(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(input_path)

    profile = get_profile(sis_profile)

    print("=== LOADING ===")
    data = _load_file(input_path)
    print(f"  Loaded {input_path.name}: {len(data):,} rows, {len(data.columns)} columns")
    data = _apply_sis_profile(data, profile)
    print(f"  SIS profile: {profile['display_name']} — column mapping applied")

    # -------------------------------------------------------------------------
    # STEP 1 — FILTER ON LEVEL (canonical UG / GR)
    # -------------------------------------------------------------------------
    print("\n=== STEP 1: FILTER ON LEVEL ===")

    data["student_id"] = normalize_str(data["student_id"])

    total_raw = len(data)

    unexpected = data[~data["level"].isin(_CANONICAL_LEVELS)]
    if len(unexpected) > 0:
        print(f"\n  Unexpected level values found ({len(unexpected):,} rows) — will be excluded:")
        print(unexpected["level"].value_counts().to_string())
        print()

    data = data[data["level"].isin(_CANONICAL_LEVELS)].copy()

    print(f"  Total raw records:       {total_raw:,}")
    print(f"  Excluded (invalid level): {total_raw - len(data):,}")
    print(f"  Valid population:        {len(data):,} students")
    print("\n  Level breakdown:")
    levl_breakdown: dict[str, int] = {}
    for code in sorted(_CANONICAL_LEVELS):
        n = int((data["level"] == code).sum())
        pct = n / len(data) * 100
        levl_breakdown[code] = n
        print(f"    {code}: {n:,}  ({pct:.1f}%)")

    # -------------------------------------------------------------------------
    # STEP 2 — TARGET VARIABLE
    # -------------------------------------------------------------------------
    print("\n=== STEP 2: DEFAULT FLAG ===")
    data["days_delinquent"] = to_numeric(data["days_delinquent"]).fillna(0)
    data["default_flag"] = (data["days_delinquent"] > DEFAULT_DAYS_THRESHOLD).astype(int)

    total = len(data)
    defaults = int(data["default_flag"].sum())
    print(f"  Definition: Days Delinquent > {DEFAULT_DAYS_THRESHOLD} (34 CFR § 682.200)")
    print(f"  Defaults:   {defaults:,}  ({defaults / total * 100:.1f}%)")
    print(f"  Current:    {total - defaults:,}  ({(total - defaults) / total * 100:.1f}%)")

    print("\n  Default rate by level:")
    default_rate_by_level: dict[str, float] = {}
    for code in sorted(_CANONICAL_LEVELS):
        sub = data[data["level"] == code]
        if len(sub) == 0:
            continue
        rate = float(sub["default_flag"].mean())
        default_rate_by_level[code] = rate
        print(f"    {code}: {rate:.1%}  ({int(sub['default_flag'].sum())} of {len(sub):,})")

    # -------------------------------------------------------------------------
    # STEP 3 — FEATURES
    # -------------------------------------------------------------------------
    print("\n=== STEP 3: FEATURES ===")

    data["program"]      = normalize_str(data["program"])
    data["major"]        = normalize_str(data["major"])
    data["student_type"] = normalize_str(data["student_type"])
    data["campus_code"]  = normalize_str(data["campus_code"])
    data["payment_plan"] = normalize_str(data["payment_plan"])

    data["gpa"]            = to_numeric(data["gpa"])
    data["credits_earned"] = to_numeric(data["credits_earned"])
    data["num_loans"]      = to_numeric(data["num_loans"])

    data["original_loan_amount"] = clean_currency(data["original_loan_amount"])
    data["current_balance"]      = clean_currency(data["current_balance"])

    grad_true = profile["graduated_true_value"].upper()
    data["graduated"] = (
        normalize_str_upper(data["graduated_ind"]) == grad_true
    ).astype(int)

    withdrawn_codes_upper = {c.upper() for c in profile["withdrawn_codes"]}
    data["withdrawn"] = (
        normalize_str_upper(data["enrollment_status"])
        .isin(withdrawn_codes_upper)
    ).astype(int)

    print("\n  Enrollment status breakdown:")
    print(data["enrollment_status"].value_counts().to_string())

    FEATURES = [
        "level", "program", "major", "student_type", "campus_code",
        "gpa", "credits_earned", "graduated", "withdrawn",
        "num_loans", "original_loan_amount", "current_balance", "payment_plan",
    ]

    print("\n  Feature completeness:")
    feature_completeness: dict[str, float] = {}
    for col in FEATURES:
        pct = float(data[col].notna().mean() * 100)
        non_null = int(data[col].notna().sum())
        bar = "█" * int(pct / BAR_SCALE)
        feature_completeness[col] = round(pct / 100, 4)
        print(f"    {col:<25} {pct:5.1f}%  ({non_null:,} non-null)  {bar}")

    # -------------------------------------------------------------------------
    # STEP 4 — SAVE
    # -------------------------------------------------------------------------
    print("\n=== STEP 4: SAVING ===")

    final_cols = ["student_id"] + FEATURES + ["default_flag"]
    dataset = data[final_cols].copy()

    out_path = session_dir / "dataset_fris.csv"
    dataset.to_csv(out_path, index=False)

    print(f"  Saved:   {out_path}")
    print(f"  Shape:   {len(dataset):,} rows × {len(final_cols)} columns")
    print(f"  SIS:     {profile['display_name']}")
    print("\n  Ready for fris_model.py")

    return {
        "total_raw": total_raw,
        "excluded_invalid_levl": total_raw - total,
        "valid_population": total,
        "levl_breakdown": levl_breakdown,
        "defaults": defaults,
        "default_rate": round(defaults / total, 4),
        "default_rate_by_level": {k: round(v, 4) for k, v in default_rate_by_level.items()},
        "feature_completeness": feature_completeness,
        "output_path": str(out_path),
        "shape": [len(dataset), len(final_cols)],
        "sis_profile": sis_profile,
    }


if __name__ == "__main__":
    result = run_etl(
        input_path=SCRIPT_DIR / "Borrower Details.xlsx",
        session_dir=SCRIPT_DIR,
        sis_profile="banner",
    )
    print(f"\n  ETL complete — {result['valid_population']:,} students, "
          f"{result['default_rate']:.1%} default rate")
