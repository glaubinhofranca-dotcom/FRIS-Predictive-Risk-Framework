"""
FRIS v1 -- Real Dataset ETL
New England College -- Student Financial Services

PRIMARY SOURCE: Borrower Details.xlsx
    Consolidated by NEC IT. Contains loan delinquency,
    academic, and enrollment data. Already deduplicated.

OUTPUT: dataset_fris.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

VALID_PREFIXES         = ("UG", "UA", "GR")  # @00 = undeposited, excluded
WITHDRAWN_CODES        = {"WD", "W4", "W6", "W7"}
DEFAULT_DAYS_THRESHOLD = 270                  # federal loan default definition

def is_valid_id(series):
    return series.astype(str).str.upper().str.startswith(VALID_PREFIXES)


# =============================================================================
# LOAD
# =============================================================================
def load(filename, **kwargs):
    path = SCRIPT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(path, **kwargs)
    else:
        df = pd.read_csv(path, low_memory=False, **kwargs)
    print(f"  Loaded {filename}: {len(df):,} rows, {len(df.columns)} columns")
    return df

print("=== LOADING ===")
all_files = sorted(SCRIPT_DIR.glob("*.csv")) + sorted(SCRIPT_DIR.glob("*.xlsx"))
print("  Files found in folder:")
for f in sorted(all_files):
    print(f"    {f.name}")
data = load("Borrower Details.xlsx")    #<--- CHANGE HERE (BE CAREFUL, SENSITIVE DATA!!!)


# =============================================================================
# STEP 1 -- FILTER
# =============================================================================
print("\n=== STEP 1: FILTER ===")
data["ID"] = data["ID"].astype(str).str.strip()
before     = len(data)
data       = data[is_valid_id(data["ID"])].copy()
print(f"  @00 excluded:     {before - len(data):,}")
print(f"  Valid population: {len(data):,} students")
print("\n  Prefix breakdown:")
for pfx in ["UG", "UA", "GR"]:
    n = data["ID"].str.startswith(pfx).sum()
    print(f"    {pfx}: {n:,}")


# =============================================================================
# STEP 2 -- TARGET VARIABLE
# =============================================================================
print("\n=== STEP 2: DEFAULT FLAG ===")
data["Days Delinquent"] = pd.to_numeric(data["Days Delinquent"], errors="coerce").fillna(0)
data["default_flag"]    = (data["Days Delinquent"] > DEFAULT_DAYS_THRESHOLD).astype(int)
total    = len(data)
defaults = data["default_flag"].sum()
print(f"  Default  (>270 days): {defaults:,}  ({defaults/total*100:.1f}%)")
print(f"  Current  (<=270 days): {total - defaults:,}  ({(total-defaults)/total*100:.1f}%)")


# =============================================================================
# STEP 3 -- FEATURES
# =============================================================================
print("\n=== STEP 3: FEATURES ===")

data["student_id"]     = data["ID"]
data["level"]          = data["LEVL_CODE"].astype(str).str.strip()
data["program"]        = data["PROGRAM"].astype(str).str.strip()
data["major"]          = data["MAJR_DESC"].astype(str).str.strip()
data["student_type"]   = data["STYP_DESC"].astype(str).str.strip()
data["campus_code"]    = data["CAMP_CODE"].astype(str).str.strip()
data["gpa"]            = pd.to_numeric(data["OVERALL_LGPA_GPA"], errors="coerce")
data["credits_earned"] = pd.to_numeric(data["OVERALL_LGPA_HOURS_EARNED"], errors="coerce")
data["num_loans"]      = pd.to_numeric(data["# of Loans"], errors="coerce")

data["original_loan_amount"] = pd.to_numeric(
    data["Original Loan Amount"].astype(str).str.replace(r"[\$,]", "", regex=True),
    errors="coerce"
)
data["current_balance"] = pd.to_numeric(
    data["Current Principal Balance"].astype(str).str.replace(r"[\$,]", "", regex=True),
    errors="coerce"
)
data["on_payment_plan"] = (
    data["Payment Plan"].astype(str).str.strip().str.upper()
    .isin(["Y", "YES", "TRUE", "1"])
).astype(int)

data["graduated"] = (
    data["GRADUATED_IND"].astype(str).str.strip().str.upper() == "Y"
).astype(int)

data["withdrawn"] = (
    data["SFBETRM_ESTS_CODE"].astype(str).str.strip().str.upper()
    .isin(WITHDRAWN_CODES)
).astype(int)

# Enrollment status breakdown for audit
print("\n  SFBETRM_ESTS_CODE breakdown:")
print(data["SFBETRM_ESTS_CODE"].value_counts().to_string())

print("\n  Feature completeness:")
features = [
    "level", "program", "major", "student_type", "campus_code",
    "gpa", "credits_earned", "graduated", "withdrawn",
    "num_loans", "original_loan_amount",
    "current_balance", "on_payment_plan",
]
for col in features:
    pct = data[col].notna().mean() * 100
    bar = "█" * int(pct / 5)
    print(f"    {col:<25} {pct:5.1f}%  {bar}")


# =============================================================================
# STEP 4 -- SAVE
# =============================================================================
print("\n=== STEP 4: SAVING ===")

final_cols = ["student_id"] + features + ["default_flag"]
dataset    = data[final_cols].copy()

out_path = SCRIPT_DIR / "dataset_fris.csv"
dataset.to_csv(out_path, index=False)
print(f"  Saved: {out_path}")
print(f"  {len(dataset):,} rows x {len(final_cols)} columns")
print("  Ready for fris_model.py")