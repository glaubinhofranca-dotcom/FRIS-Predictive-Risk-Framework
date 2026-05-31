"""
FRIS v3 — Exploratory Data Analysis
New England College · Student Financial Services

INPUT:  dataset_fris.csv   (produced by fris_etl.py)
OUTPUT: dict (no files written — results returned for API/dashboard)
"""

import pandas as pd
import numpy as np
from pathlib import Path

NUMERIC_COLS = [
    "gpa",
    "original_loan_amount",
    "current_balance",
    "credits_earned",
    "num_loans",
]

CORRELATION_COLS = [
    "gpa",
    "credits_earned",
    "original_loan_amount",
    "current_balance",
    "num_loans",
    "graduated",
    "withdrawn",
]


def run_eda(data_path: Path) -> dict:
    """
    Compute exploratory statistics on the cleaned dataset.

    Parameters
    ----------
    data_path : Path
        Path to dataset_fris.csv produced by run_etl().

    Returns
    -------
    dict
        EDA metrics for the API / dashboard.
    """
    df = pd.read_csv(data_path, low_memory=False)

    print("=== EDA ===")
    print(f"  Rows: {len(df):,}  |  Columns: {len(df.columns)}")

    # Class balance
    vc = df["default_flag"].value_counts()
    total = len(df)
    class_balance = {
        str(k): {"n": int(v), "pct": round(v / total, 4)}
        for k, v in vc.items()
    }
    print(f"  Default rate: {df['default_flag'].mean():.1%}")

    # Missing values
    missing_values: dict[str, dict] = {}
    for col in df.columns:
        miss_n = int(df[col].isna().sum())
        missing_values[col] = {
            "missing_n": miss_n,
            "missing_pct": round(miss_n / total, 4),
        }

    # Distributions for key numeric features
    distributions: dict[str, dict] = {}
    for col in NUMERIC_COLS:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        distributions[col] = {
            "min":    round(float(s.min()), 4),
            "max":    round(float(s.max()), 4),
            "mean":   round(float(s.mean()), 4),
            "median": round(float(s.median()), 4),
            "std":    round(float(s.std()), 4),
            "p25":    round(float(s.quantile(0.25)), 4),
            "p75":    round(float(s.quantile(0.75)), 4),
        }
        print(f"  {col:<28} mean={distributions[col]['mean']:.2f}  "
              f"median={distributions[col]['median']:.2f}  "
              f"std={distributions[col]['std']:.2f}")

    # Pearson correlations with default_flag
    correlations_with_default: dict[str, float] = {}
    for col in CORRELATION_COLS:
        if col not in df.columns:
            continue
        valid = df[[col, "default_flag"]].dropna()
        if len(valid) < 2:
            continue
        r = float(np.corrcoef(valid[col].astype(float), valid["default_flag"])[0, 1])
        correlations_with_default[col] = round(r, 4)

    print("\n  Correlations with default_flag:")
    for col, r in sorted(correlations_with_default.items(), key=lambda x: abs(x[1]), reverse=True):
        direction = "+" if r >= 0 else "-"
        bar = "█" * int(abs(r) * 40)
        print(f"    {col:<28} {direction}{abs(r):.4f}  {bar}")

    print("=== EDA DONE ===")

    return {
        "n_rows": total,
        "n_cols": len(df.columns),
        "class_balance": class_balance,
        "missing_values": missing_values,
        "distributions": distributions,
        "correlations_with_default": correlations_with_default,
    }


if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).parent
    result = run_eda(SCRIPT_DIR / "dataset_fris.csv")
    print(f"\n  EDA complete — {result['n_rows']:,} rows analysed")
