"""
FRIS v3 — Segmentation Analysis
New England College · Student Financial Services

CHANGE FROM v2:
    The 'level' segmentation panel now explicitly labels its source as LEVL_CODE
    (Banner authoritative field). The breakdown reflects actual Banner-recorded
    academic levels rather than inferred ID prefixes.

INPUT:  dataset_fris.csv   (produced by fris_etl.py)
OUTPUT: fris_segmentation.png
        fris_segmentation.csv
"""

import warnings
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from pathlib import Path
from matplotlib.patches import Patch

SCRIPT_DIR = Path(__file__).parent

LEVEL_LABELS = {
    "UG": "UG — Undergraduate",
    "GR": "GR — Graduate",
}

# IDR detection — Banner stores full plan names, not short codes.
# Matching on substrings covers all IBR, PAYE, REPAYE, SAVE, ICR variants.
IDR_PATTERN = (
    r"income.based repayment"
    r"|pay as you earn"
    r"|revised pay as you earn"
    r"|income contingent"
    r"|saving on a valuable education"
)

BLUE  = "#378ADD"
RED   = "#E24B4A"
AMBER = "#EF9F27"
GREEN = "#1D9E75"
GRAY  = "#888780"

PCT_FORMATTER = plt.FuncFormatter(lambda x, _: f"{x:.0%}")

MIN_N_DEFAULT = 5
MIN_N_PROGRAM = 10


def _segment(df: pd.DataFrame, group_col: str, label: str, min_n: int = MIN_N_DEFAULT) -> pd.DataFrame:
    """Default rate per group, sorted descending, filtered to min_n."""
    g = (df.groupby(group_col, observed=True)["default_flag"]
           .agg(count="count", defaults="sum")
           .reset_index())
    g["default_rate"] = g["defaults"] / g["count"]
    g = g[g["count"] >= min_n].sort_values("default_rate", ascending=False)
    g.columns = [label, "n", "defaults", "default_rate"]
    return g


def _bar_colors(rates, overall: float) -> list[str]:
    return [RED if r > overall + 0.03 else GREEN if r < overall - 0.03 else AMBER
            for r in rates]


def _add_labels(ax, bars, rates) -> None:
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_width() + 0.003,
                bar.get_y() + bar.get_height() / 2,
                f"{rate:.1%}", va="center", ha="left", fontsize=8)


def run_segmentation(data_path: Path, session_dir: Path) -> dict:
    """
    Compute segmentation analysis and produce charts/CSV.

    Parameters
    ----------
    data_path : Path
        Path to dataset_fris.csv produced by run_etl().
    session_dir : Path
        Directory for output files (PNG + CSV).

    Returns
    -------
    dict
        Segmentation metrics for the API / dashboard.
    """
    session_dir = Path(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    out_png = session_dir / "fris_segmentation.png"
    out_csv = session_dir / "fris_segmentation.csv"

    df = pd.read_csv(data_path, low_memory=False)
    print(f"Loaded: {len(df):,} students | Default rate: {df['default_flag'].mean():.1%}")
    print(f"\nLevel distribution (from LEVL_CODE · Banner authoritative field):")
    print(df["level"].value_counts().to_string())

    df["level_label"] = df["level"].map(LEVEL_LABELS).fillna(df["level"])

    df["gpa_band"] = pd.cut(
        df["gpa"],
        bins=[0, 2.0, 2.5, 3.0, 3.5, 4.0],
        labels=["< 2.0", "2.0–2.5", "2.5–3.0", "3.0–3.5", "3.5–4.0"],
    )

    df["loan_band"] = pd.cut(
        df["original_loan_amount"],
        bins=[0, 5000, 15000, 30000, 50000, 999_999],
        labels=["< $5K", "$5K–$15K", "$15K–$30K", "$30K–$50K", "> $50K"],
    )

    df["idr_enrolled"] = (
        df["payment_plan"]
        .astype(str).str.strip().str.lower()
        .str.contains(IDR_PATTERN, regex=True, na=False)
    )

    OVERALL = float(df["default_flag"].mean())

    segs = {
        "Level (LEVL_CODE)": _segment(df, "level_label", "Level (LEVL_CODE)"),
        "Student type":      _segment(df, "student_type", "Student type"),
        "Campus":            _segment(df, "campus_code", "Campus"),
        "GPA band":          _segment(df, "gpa_band", "GPA band"),
        "Loan amount":       _segment(df, "loan_band", "Loan amount"),
        "Payment plan":      _segment(df, "payment_plan", "Payment plan"),
        "Program":           _segment(df, "program", "Program", min_n=MIN_N_PROGRAM),
    }

    # Graduation / withdrawal (binary flags — built manually)
    from typing import NamedTuple

    class StatusRow(NamedTuple):
        label: str
        rate: float
        n: int
        defaults: int

    status_rows = [
        StatusRow("Not graduated",  float(df[df["graduated"] == 0]["default_flag"].mean()),
                  int((df["graduated"] == 0).sum()), int(df[df["graduated"] == 0]["default_flag"].sum())),
        StatusRow("Graduated",      float(df[df["graduated"] == 1]["default_flag"].mean()),
                  int((df["graduated"] == 1).sum()), int(df[df["graduated"] == 1]["default_flag"].sum())),
        StatusRow("Not withdrawn",  float(df[df["withdrawn"] == 0]["default_flag"].mean()),
                  int((df["withdrawn"] == 0).sum()), int(df[df["withdrawn"] == 0]["default_flag"].sum())),
        StatusRow("Withdrawn",      float(df[df["withdrawn"] == 1]["default_flag"].mean()),
                  int((df["withdrawn"] == 1).sum()), int(df[df["withdrawn"] == 1]["default_flag"].sum())),
    ]

    idr_mask = df["idr_enrolled"]
    idr_rate = float(df[idr_mask]["default_flag"].mean())
    non_idr_rate = float(df[~idr_mask]["default_flag"].mean())
    idr_n = int(idr_mask.sum())
    non_idr_n = int((~idr_mask).sum())

    # -------------------------------------------------------------------------
    # PRINT REPORT
    # -------------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"  Overall default rate: {OVERALL:.1%}  (n={len(df):,}  |  {df['default_flag'].sum()} defaults)")
    print(f"{'='*60}")

    for title, tbl in segs.items():
        print(f"\n── {title} {'─'*(54-len(title))}")
        for _, row in tbl.iterrows():
            val = row.iloc[0]
            rate = row["default_rate"]
            n = int(row["n"])
            d = int(row["defaults"])
            delta = rate - OVERALL
            flag = " ▲" if delta > 0.03 else (" ▼" if delta < -0.03 else "")
            print(f"  {str(val):<38} {rate:5.1%}  n={n:<5} ({d} defaults){flag}")

    print(f"\n── Graduation / Withdrawal Status {'─'*26}")
    for row in status_rows:
        delta = row.rate - OVERALL
        flag = " ▲" if delta > 0.03 else (" ▼" if delta < -0.03 else "")
        print(f"  {row.label:<38} {row.rate:5.1%}  n={row.n:<5} ({row.defaults} defaults){flag}")

    print(f"\n── Income-Driven Repayment (IDR) Policy Finding {'─'*12}")
    print(f"  IDR plans (IBR/REPAYE/PAYE/SAVE/ICR): {idr_rate:.1%}  (n={idr_n:,})")
    print(f"  Non-IDR (Standard, Graduated, etc.):  {non_idr_rate:.1%}  (n={non_idr_n:,})")

    # -------------------------------------------------------------------------
    # EXPORT CSV
    # -------------------------------------------------------------------------
    all_rows = []
    for title, tbl in segs.items():
        tmp = tbl.copy()
        tmp.insert(0, "Segment", title)
        tmp.columns = ["Segment", "Value", "n", "Defaults", "Default Rate"]
        all_rows.append(tmp)

    status_df = pd.DataFrame([
        {"Segment": "Graduation / Withdrawal", "Value": r.label,
         "n": r.n, "Defaults": r.defaults, "Default Rate": f"{r.rate:.1%}"}
        for r in status_rows
    ])
    all_rows.append(status_df)

    idr_df = pd.DataFrame([
        {"Segment": "IDR Policy Finding", "Value": "IDR enrolled",
         "n": idr_n, "Defaults": int(df[idr_mask]["default_flag"].sum()),
         "Default Rate": f"{idr_rate:.1%}"},
        {"Segment": "IDR Policy Finding", "Value": "Non-IDR",
         "n": non_idr_n, "Defaults": int(df[~idr_mask]["default_flag"].sum()),
         "Default Rate": f"{non_idr_rate:.1%}"},
    ])
    all_rows.append(idr_df)

    export = pd.concat(all_rows, ignore_index=True)
    export["Default Rate"] = export["Default Rate"].apply(
        lambda x: x if isinstance(x, str) else f"{x:.1%}"
    )
    export.to_csv(out_csv, index=False)
    print(f"\nCSV saved: {out_csv}")

    # -------------------------------------------------------------------------
    # VISUALIZATION — 9 panels
    # -------------------------------------------------------------------------
    overall_line = dict(color=GRAY, linestyle="--", linewidth=1, label=f"Overall {OVERALL:.1%}")

    fig = plt.figure(figsize=(18, 24))
    fig.suptitle(
        f"FRIS v3 — Default Rate Segmentation · New England College\n"
        f"'Level' column sourced from LEVL_CODE (Banner authoritative academic level field)",
        fontsize=14, fontweight="bold", y=0.99,
    )
    gs = gridspec.GridSpec(5, 2, figure=fig, hspace=0.55, wspace=0.35)

    def _panel(ax, labels, rates, title, legend=False):
        b = ax.barh(labels, rates, color=_bar_colors(rates, OVERALL), height=0.5)
        ax.axvline(OVERALL, **overall_line)
        ax.set_title(title, fontsize=11, fontweight="500")
        ax.set_xlabel("Default rate")
        ax.xaxis.set_major_formatter(PCT_FORMATTER)
        _add_labels(ax, b, rates)
        if legend:
            ax.legend(fontsize=8)

    t = segs["Level (LEVL_CODE)"]
    _panel(fig.add_subplot(gs[0, 0]), t["Level (LEVL_CODE)"], t["default_rate"],
           "By academic level (LEVL_CODE · Banner)", legend=True)

    t = segs["Student type"]
    ax = fig.add_subplot(gs[0, 1])
    _panel(ax, t["Student type"], t["default_rate"], "By student type")
    ax.tick_params(axis="y", labelsize=8)

    t = segs["Campus"]
    _panel(fig.add_subplot(gs[1, 0]), t["Campus"], t["default_rate"], "By campus code")

    t = segs["GPA band"].sort_values("GPA band")
    _panel(fig.add_subplot(gs[1, 1]), t["GPA band"], t["default_rate"], "By GPA band")

    t = segs["Loan amount"]
    _panel(fig.add_subplot(gs[2, 0]), t["Loan amount"], t["default_rate"],
           "By original loan amount")

    labels = [r.label for r in status_rows]
    rates = [r.rate for r in status_rows]
    _panel(fig.add_subplot(gs[2, 1]), labels, rates,
           "By graduation / withdrawal status")

    t = segs["Payment plan"]
    ax = fig.add_subplot(gs[3, 0])
    _panel(ax, t["Payment plan"], t["default_rate"],
           "By payment plan · IDR = 0% default (policy finding)")
    ax.tick_params(axis="y", labelsize=8)

    ax = fig.add_subplot(gs[3, 1])
    idr_labels = ["IDR plans\n(IBR / REPAYE / PAYE)", "Non-IDR\n(Standard / Graduated)"]
    idr_rates = [idr_rate, non_idr_rate]
    b = ax.barh(idr_labels, idr_rates, color=[GREEN, RED], height=0.4)
    ax.axvline(OVERALL, **overall_line)
    ax.set_title("IDR policy finding · Income-Driven Repayment", fontsize=11, fontweight="500")
    ax.set_xlabel("Default rate")
    ax.xaxis.set_major_formatter(PCT_FORMATTER)
    _add_labels(ax, b, idr_rates)
    ax.legend(fontsize=8)

    t = segs["Program"].head(15)
    ax = fig.add_subplot(gs[4, :])
    _panel(ax, t["Program"], t["default_rate"],
           "By program · top 15 by default rate (min n=10)")
    ax.tick_params(axis="y", labelsize=8)

    fig.legend(handles=[
        Patch(color=RED,   label=f"Above average (> {OVERALL+0.03:.0%})"),
        Patch(color=AMBER, label="Near average"),
        Patch(color=GREEN, label=f"Below average (< {OVERALL-0.03:.0%})"),
    ], loc="lower center", ncol=3, fontsize=9, bbox_to_anchor=(0.5, 0.003))

    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close("all")
    print(f"Chart saved: {out_png}")
    print("=== DONE ===")

    # -------------------------------------------------------------------------
    # BUILD RETURN DICT
    # -------------------------------------------------------------------------
    def _seg_to_list(tbl: pd.DataFrame, value_col: str) -> list[dict]:
        return [
            {
                "value": str(row[value_col]),
                "n": int(row["n"]),
                "defaults": int(row["defaults"]),
                "default_rate": round(float(row["default_rate"]), 4),
            }
            for _, row in tbl.iterrows()
        ]

    return {
        "overall_default_rate": round(OVERALL, 4),
        "total_students": len(df),
        "total_defaults": int(df["default_flag"].sum()),
        "idr_rate": round(idr_rate, 4),
        "non_idr_rate": round(non_idr_rate, 4),
        "idr_differential": round(non_idr_rate - idr_rate, 4),
        "idr_n": idr_n,
        "non_idr_n": non_idr_n,
        "segments": {
            "level":       _seg_to_list(segs["Level (LEVL_CODE)"], "Level (LEVL_CODE)"),
            "student_type": _seg_to_list(segs["Student type"], "Student type"),
            "campus":      _seg_to_list(segs["Campus"], "Campus"),
            "gpa_band":    _seg_to_list(segs["GPA band"], "GPA band"),
            "loan_amount": _seg_to_list(segs["Loan amount"], "Loan amount"),
            "payment_plan": _seg_to_list(segs["Payment plan"], "Payment plan"),
            "program":     _seg_to_list(segs["Program"], "Program"),
            "graduation_status": [
                {"value": r.label, "n": r.n, "defaults": r.defaults,
                 "default_rate": round(r.rate, 4)}
                for r in status_rows
            ],
        },
        "chart_path": str(out_png),
        "csv_path": str(out_csv),
    }


if __name__ == "__main__":
    result = run_segmentation(
        data_path=SCRIPT_DIR / "dataset_fris.csv",
        session_dir=SCRIPT_DIR,
    )
    print(f"\n  Overall default rate: {result['overall_default_rate']:.1%}")
    print(f"  IDR differential: {result['idr_differential']:.1%}")
