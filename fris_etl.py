"""
FRIS v3 — ETL Pipeline
New England College · Student Financial Services

CHANGE FROM v2:
    Academic level is now determined exclusively by LEVL_CODE (Banner authoritative field).
    The previous version used the student ID prefix (UG/GR) to filter and classify
    students, which was a proxy. LEVL_CODE is the canonical source in Banner/Ellucian.

PRIMARY SOURCE: Borrower Details.xlsx
    Consolidated by NEC IT from Banner/Ellucian + loan servicer exports.
    Already deduplicated at the student level.

OUTPUT: dataset_fris.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Academic level codes in Banner/Ellucian
# UG = Undergraduate  |  GR = Graduate
# @00-prefixed IDs = undeposited prospects with no federal loans — excluded at source
VALID_LEVL_CODES = {"UG", "GR"}
WITHDRAWN_CODES = {"WD", "W4", "W6", "W7"}
DEFAULT_DAYS_THRESHOLD = 270  # 34 CFR § 682.200 — federal loan default definition

BAR_SCALE = 5  # chars per percentage point in progress bars


def _load_file(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, **kwargs)
    return pd.read_csv(path, low_memory=False, **kwargs)


def clean_currency(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(r"[\$,]", "", regex=True),
        errors="coerce",
    )


def run_etl(input_path: Path, session_dir: Path) -> dict:
    """
    Run the full ETL pipeline.

    Parameters
    ----------
    input_path : Path
        Path to the raw borrower data file (.xlsx or .csv).
    session_dir : Path
        Directory where dataset_fris.csv will be written.

    Returns
    -------
    dict
        Pipeline metrics for the API / dashboard.
    """
    session_dir = Path(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(input_path)

    print("=== LOADING ===")
    data = _load_file(input_path)
    print(f"  Loaded {input_path.name}: {len(data):,} rows, {len(data.columns)} columns")

    # -------------------------------------------------------------------------
    # STEP 1 — FILTER ON LEVL_CODE
    # -------------------------------------------------------------------------
    print("\n=== STEP 1: FILTER ON LEVL_CODE ===")

    data["LEVL_CODE"] = data["LEVL_CODE"].astype(str).str.strip().str.upper()
    data["ID"] = data["ID"].astype(str).str.strip()

    total_raw = len(data)

    unexpected = data[~data["LEVL_CODE"].isin(VALID_LEVL_CODES)]
    if len(unexpected) > 0:
        print(f"\n  Unexpected LEVL_CODE values found ({len(unexpected):,} rows) — will be excluded:")
        print(unexpected["LEVL_CODE"].value_counts().to_string())
        print()

    data = data[data["LEVL_CODE"].isin(VALID_LEVL_CODES)].copy()

    print(f"  Total raw records:       {total_raw:,}")
    print(f"  Excluded (invalid LEVL): {total_raw - len(data):,}")
    print(f"  Valid population:        {len(data):,} students")
    print("\n  LEVL_CODE breakdown (from Banner):")
    levl_breakdown: dict[str, int] = {}
    for code in sorted(VALID_LEVL_CODES):
        n = int((data["LEVL_CODE"] == code).sum())
        pct = n / len(data) * 100
        levl_breakdown[code] = n
        print(f"    {code}: {n:,}  ({pct:.1f}%)")

    # -------------------------------------------------------------------------
    # STEP 2 — TARGET VARIABLE
    # -------------------------------------------------------------------------
    print("\n=== STEP 2: DEFAULT FLAG ===")
    data["Days Delinquent"] = pd.to_numeric(data["Days Delinquent"], errors="coerce").fillna(0)
    data["default_flag"] = (data["Days Delinquent"] > DEFAULT_DAYS_THRESHOLD).astype(int)

    total = len(data)
    defaults = int(data["default_flag"].sum())
    print(f"  Definition: Days Delinquent > {DEFAULT_DAYS_THRESHOLD} (34 CFR § 682.200)")
    print(f"  Defaults:   {defaults:,}  ({defaults / total * 100:.1f}%)")
    print(f"  Current:    {total - defaults:,}  ({(total - defaults) / total * 100:.1f}%)")

    print("\n  Default rate by LEVL_CODE:")
    default_rate_by_level: dict[str, float] = {}
    for code in sorted(VALID_LEVL_CODES):
        sub = data[data["LEVL_CODE"] == code]
        rate = float(sub["default_flag"].mean())
        default_rate_by_level[code] = rate
        print(f"    {code}: {rate:.1%}  ({int(sub['default_flag'].sum())} of {len(sub):,})")

    # -------------------------------------------------------------------------
    # STEP 3 — FEATURES
    # -------------------------------------------------------------------------
    print("\n=== STEP 3: FEATURES ===")

    data["student_id"] = data["ID"]
    data["level"] = data["LEVL_CODE"]
    data["program"] = data["PROGRAM"].astype(str).str.strip()
    data["major"] = data["MAJR_DESC"].astype(str).str.strip()
    data["student_type"] = data["STYP_DESC"].astype(str).str.strip()
    data["campus_code"] = data["CAMP_CODE"].astype(str).str.strip()

    data["gpa"] = pd.to_numeric(data["OVERALL_LGPA_GPA"], errors="coerce")
    data["credits_earned"] = pd.to_numeric(data["OVERALL_LGPA_HOURS_EARNED"], errors="coerce")
    data["num_loans"] = pd.to_numeric(data["# of Loans"], errors="coerce")

    data["original_loan_amount"] = clean_currency(data["Original Loan Amount"])
    data["current_balance"] = clean_currency(data["Current Principal Balance"])

    data["payment_plan"] = data["Payment Plan"].astype(str).str.strip()

    data["graduated"] = (
        data["GRADUATED_IND"].astype(str).str.strip().str.upper() == "Y"
    ).astype(int)

    data["withdrawn"] = (
        data["SFBETRM_ESTS_CODE"].astype(str).str.strip().str.upper()
        .isin(WITHDRAWN_CODES)
    ).astype(int)

    print("\n  Enrollment status (SFBETRM_ESTS_CODE) breakdown:")
    print(data["SFBETRM_ESTS_CODE"].value_counts().to_string())

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
    print(f"  Level column source: LEVL_CODE (Banner authoritative field)")
    print("\n  Sample — level value distribution in output dataset:")
    print(dataset["level"].value_counts().to_string())
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
    }


if __name__ == "__main__":
    result = run_etl(
        input_path=SCRIPT_DIR / "Borrower Details.xlsx",
        session_dir=SCRIPT_DIR,
    )
    print(f"\n  ETL complete — {result['valid_population']:,} students, "
          f"{result['default_rate']:.1%} default rate")
