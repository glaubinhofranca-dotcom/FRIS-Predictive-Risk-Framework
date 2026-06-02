"""
FRIS — Shared data-cleaning utilities.
"""

import pandas as pd


def normalize_str(series: pd.Series) -> pd.Series:
    """Strip whitespace from a string series."""
    return series.astype(str).str.strip()


def normalize_str_upper(series: pd.Series) -> pd.Series:
    """Strip whitespace and uppercase a string series."""
    return series.astype(str).str.strip().str.upper()


def to_numeric(series: pd.Series) -> pd.Series:
    """Coerce to numeric; non-parseable values become NaN."""
    return pd.to_numeric(series, errors="coerce")


def clean_currency(series: pd.Series) -> pd.Series:
    """Remove $ and , then coerce to numeric."""
    return pd.to_numeric(
        series.astype(str).str.replace(r"[\$,]", "", regex=True),
        errors="coerce",
    )
