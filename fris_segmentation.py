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

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_FILE  = SCRIPT_DIR / "dataset_fris.csv"
OUT_PNG    = SCRIPT_DIR / "fris_segmentation.png"
OUT_CSV    = SCRIPT_DIR / "fris_segmentation.csv"

# Banner LEVL_CODE values and their labels
LEVEL_LABELS = {
    "UG": "UG — Undergraduate",
    "GR": "GR — Graduate",
}


# =============================================================================
# LOAD
# =============================================================================
df = pd.read_csv(DATA_FILE, low_memory=False)
print(f"Loaded: {len(df):,} students | Default rate: {df['default_flag'].mean():.1%}")
print(f"\nLevel distribution (from LEVL_CODE · Banner authoritative field):")
print(df["level"].value_counts().to_string())

# Apply readable labels for the level column in charts
df["level_label"] = df["level"].map(LEVEL_LABELS).fillna(df["level"])

# GPA bands
df["gpa_band"] = pd.cut(
    df["gpa"],
    bins=[0, 2.0, 2.5, 3.0, 3.5, 4.0],
    labels=["< 2.0", "2.0–2.5", "2.5–3.0", "3.0–3.5", "3.5–4.0"]
)

# Loan amount bands
df["loan_band"] = pd.cut(
    df["original_loan_amount"],
    bins=[0, 5000, 15000, 30000, 50000, 999_999],
    labels=["< $5K", "$5K–$15K", "$15K–$30K", "$30K–$50K", "> $50K"]
)

# IDR flag (Income-Driven Repayment)
# IDR detection — Banner stores full plan names, not short codes.
# Matching on substrings covers all IBR, PAYE, REPAYE, SAVE, ICR variants.
IDR_PATTERN = (
    r"income.based repayment"      # IBR variants
    r"|pay as you earn"            # PAYE / REPAYE variants
    r"|revised pay as you earn"    # REPAYE
    r"|income contingent"          # ICR
    r"|saving on a valuable education"  # SAVE
)
df["idr_enrolled"] = (
    df["payment_plan"]
    .astype(str).str.strip().str.lower()
    .str.contains(IDR_PATTERN, regex=True, na=False)
)


# =============================================================================
# SEGMENTATION HELPER
# =============================================================================
def segment(group_col, label, min_n=5):
    """Default rate per group, sorted descending, filtered to min_n."""
    g = (df.groupby(group_col, observed=True)["default_flag"]
           .agg(count="count", defaults="sum")
           .reset_index())
    g["default_rate"] = g["defaults"] / g["count"]
    g = g[g["count"] >= min_n].sort_values("default_rate", ascending=False)
    g.columns = [label, "n", "defaults", "default_rate"]
    return g


OVERALL = df["default_flag"].mean()

segs = {
    "Level (LEVL_CODE)": segment("level_label",   "Level (LEVL_CODE)"),
    "Student type":      segment("student_type",   "Student type"),
    "Campus":            segment("campus_code",    "Campus"),
    "GPA band":          segment("gpa_band",       "GPA band"),
    "Loan amount":       segment("loan_band",       "Loan amount"),
    "Payment plan":      segment("payment_plan",   "Payment plan"),
    "Program":           segment("program",        "Program", min_n=10),
}

# Graduation / withdrawn (binary, built manually)
status_rows = [
    ("Not graduated",  df[df["graduated"] == 0]["default_flag"].mean(),
     (df["graduated"] == 0).sum(), (df[df["graduated"] == 0]["default_flag"]).sum()),
    ("Graduated",      df[df["graduated"] == 1]["default_flag"].mean(),
     (df["graduated"] == 1).sum(), (df[df["graduated"] == 1]["default_flag"]).sum()),
    ("Not withdrawn",  df[df["withdrawn"] == 0]["default_flag"].mean(),
     (df["withdrawn"] == 0).sum(), (df[df["withdrawn"] == 0]["default_flag"]).sum()),
    ("Withdrawn",      df[df["withdrawn"] == 1]["default_flag"].mean(),
     (df["withdrawn"] == 1).sum(), (df[df["withdrawn"] == 1]["default_flag"]).sum()),
]

# IDR analysis
idr_rate     = df[df["idr_enrolled"]]["default_flag"].mean()
non_idr_rate = df[~df["idr_enrolled"]]["default_flag"].mean()


# =============================================================================
# PRINT REPORT
# =============================================================================
print(f"\n{'='*60}")
print(f"  Overall default rate: {OVERALL:.1%}  (n={len(df):,}  |  {df['default_flag'].sum()} defaults)")
print(f"{'='*60}")

for title, tbl in segs.items():
    print(f"\n── {title} {'─'*(54-len(title))}")
    for _, row in tbl.iterrows():
        val   = row.iloc[0]
        rate  = row["default_rate"]
        n     = int(row["n"])
        d     = int(row["defaults"])
        delta = rate - OVERALL
        flag  = " ▲" if delta > 0.03 else (" ▼" if delta < -0.03 else "")
        print(f"  {str(val):<38} {rate:5.1%}  n={n:<5} ({d} defaults){flag}")

print(f"\n── Graduation / Withdrawal Status {'─'*26}")
for label, rate, n, d in status_rows:
    delta = rate - OVERALL
    flag  = " ▲" if delta > 0.03 else (" ▼" if delta < -0.03 else "")
    print(f"  {label:<38} {rate:5.1%}  n={int(n):<5} ({int(d)} defaults){flag}")

print(f"\n── Income-Driven Repayment (IDR) Policy Finding {'─'*12}")
print(f"  IDR plans (IBR/REPAYE/PAYE/SAVE/ICR): {idr_rate:.1%}  "
      f"(n={df['idr_enrolled'].sum():,})")
print(f"  Non-IDR (Standard, Graduated, etc.):  {non_idr_rate:.1%}  "
      f"(n={(~df['idr_enrolled']).sum():,})")


# =============================================================================
# EXPORT CSV
# =============================================================================
all_rows = []
for title, tbl in segs.items():
    tmp = tbl.copy()
    tmp.insert(0, "Segment", title)
    tmp.columns = ["Segment", "Value", "n", "Defaults", "Default Rate"]
    all_rows.append(tmp)

# Add graduation/withdrawal manually
status_df = pd.DataFrame([
    {"Segment": "Graduation / Withdrawal", "Value": lbl,
     "n": int(n), "Defaults": int(d), "Default Rate": f"{r:.1%}"}
    for lbl, r, n, d in status_rows
])
all_rows.append(status_df)

# Add IDR finding
idr_df = pd.DataFrame([
    {"Segment": "IDR Policy Finding", "Value": "IDR enrolled",
     "n": int(df["idr_enrolled"].sum()), "Defaults": int(df[df["idr_enrolled"]]["default_flag"].sum()),
     "Default Rate": f"{idr_rate:.1%}"},
    {"Segment": "IDR Policy Finding", "Value": "Non-IDR",
     "n": int((~df["idr_enrolled"]).sum()), "Defaults": int(df[~df["idr_enrolled"]]["default_flag"].sum()),
     "Default Rate": f"{non_idr_rate:.1%}"},
])
all_rows.append(idr_df)

export = pd.concat(all_rows, ignore_index=True)
if "Default Rate" in export.columns:
    export["Default Rate"] = export["Default Rate"].apply(
        lambda x: x if isinstance(x, str) else f"{x:.1%}"
    )
export.to_csv(OUT_CSV, index=False)
print(f"\nCSV saved: {OUT_CSV}")


# =============================================================================
# VISUALIZATION — 9 panels
# =============================================================================
BLUE  = "#378ADD"
RED   = "#E24B4A"
AMBER = "#EF9F27"
GREEN = "#1D9E75"
GRAY  = "#888780"

def bar_colors(rates, overall=OVERALL):
    return [RED   if r > overall + 0.03
            else GREEN if r < overall - 0.03
            else AMBER for r in rates]

def add_labels(ax, bars, rates):
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_width() + 0.003,
                bar.get_y() + bar.get_height() / 2,
                f"{rate:.1%}", va="center", ha="left", fontsize=8)

overall_line = dict(color=GRAY, linestyle="--", linewidth=1,
                    label=f"Overall {OVERALL:.1%}")

fig = plt.figure(figsize=(18, 24))
fig.suptitle(
    f"FRIS v3 — Default Rate Segmentation · New England College\n"
    f"'Level' column sourced from LEVL_CODE (Banner authoritative academic level field)",
    fontsize=14, fontweight="bold", y=0.99
)
gs = gridspec.GridSpec(5, 2, figure=fig, hspace=0.55, wspace=0.35)


# 1 — Level (LEVL_CODE)
ax = fig.add_subplot(gs[0, 0])
t  = segs["Level (LEVL_CODE)"]
b  = ax.barh(t["Level (LEVL_CODE)"], t["default_rate"],
             color=bar_colors(t["default_rate"]), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By academic level (LEVL_CODE · Banner)", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_labels(ax, b, t["default_rate"])
ax.legend(fontsize=8)

# 2 — Student type
ax = fig.add_subplot(gs[0, 1])
t  = segs["Student type"]
b  = ax.barh(t["Student type"], t["default_rate"],
             color=bar_colors(t["default_rate"]), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By student type", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_labels(ax, b, t["default_rate"])
ax.tick_params(axis="y", labelsize=8)

# 3 — Campus
ax = fig.add_subplot(gs[1, 0])
t  = segs["Campus"]
b  = ax.barh(t["Campus"], t["default_rate"],
             color=bar_colors(t["default_rate"]), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By campus code", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_labels(ax, b, t["default_rate"])

# 4 — GPA band
ax = fig.add_subplot(gs[1, 1])
t  = segs["GPA band"].sort_values("GPA band")
b  = ax.barh(t["GPA band"], t["default_rate"],
             color=bar_colors(t["default_rate"]), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By GPA band", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_labels(ax, b, t["default_rate"])

# 5 — Loan amount band
ax = fig.add_subplot(gs[2, 0])
t  = segs["Loan amount"]
b  = ax.barh(t["Loan amount"], t["default_rate"],
             color=bar_colors(t["default_rate"]), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By original loan amount", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_labels(ax, b, t["default_rate"])

# 6 — Graduation / withdrawal status
ax = fig.add_subplot(gs[2, 1])
labels = [r[0] for r in status_rows]
rates  = [r[1] for r in status_rows]
b  = ax.barh(labels, rates, color=bar_colors(rates), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By graduation / withdrawal status", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_labels(ax, b, rates)

# 7 — Payment plan
ax = fig.add_subplot(gs[3, 0])
t  = segs["Payment plan"]
b  = ax.barh(t["Payment plan"], t["default_rate"],
             color=bar_colors(t["default_rate"]), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By payment plan · IDR = 0% default (policy finding)", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_labels(ax, b, t["default_rate"])
ax.tick_params(axis="y", labelsize=8)

# 8 — IDR vs non-IDR highlight
ax = fig.add_subplot(gs[3, 1])
idr_labels = ["IDR plans\n(IBR / REPAYE / PAYE)", "Non-IDR\n(Standard / Graduated)"]
idr_rates  = [idr_rate, non_idr_rate]
b = ax.barh(idr_labels, idr_rates,
            color=[GREEN, RED], height=0.4)
ax.axvline(OVERALL, **overall_line)
ax.set_title("IDR policy finding · Income-Driven Repayment", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_labels(ax, b, idr_rates)
ax.legend(fontsize=8)

# 9 — Top programs (full width)
ax = fig.add_subplot(gs[4, :])
t  = segs["Program"].head(15)
b  = ax.barh(t["Program"], t["default_rate"],
             color=bar_colors(t["default_rate"]), height=0.6)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By program · top 15 by default rate (min n=10)", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
ax.tick_params(axis="y", labelsize=8)
add_labels(ax, b, t["default_rate"])

# Legend
from matplotlib.patches import Patch
fig.legend(handles=[
    Patch(color=RED,   label=f"Above average (> {OVERALL+0.03:.0%})"),
    Patch(color=AMBER, label="Near average"),
    Patch(color=GREEN, label=f"Below average (< {OVERALL-0.03:.0%})"),
], loc="lower center", ncol=3, fontsize=9, bbox_to_anchor=(0.5, 0.003))

plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
print(f"Chart saved: {OUT_PNG}")
print("=== DONE ===")
