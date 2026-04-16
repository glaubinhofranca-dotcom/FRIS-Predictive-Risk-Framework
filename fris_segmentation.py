"""
FRIS v2 -- Segmentation Analysis
New England College -- Student Financial Services

INPUT:  dataset_fris.csv
OUTPUT: segmentation_fris.png
        segmentation_fris.csv  (full table for Excel)
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
OUT_PNG    = SCRIPT_DIR / "segmentation_fris.png"
OUT_CSV    = SCRIPT_DIR / "segmentation_fris.csv"

# =============================================================================
# LOAD
# =============================================================================
df = pd.read_csv(DATA_FILE, low_memory=False)
print(f"Loaded: {len(df):,} students | Default rate: {df['default_flag'].mean():.1%}")

# GPA bands
df["gpa_band"] = pd.cut(
    df["gpa"], bins=[0, 2.0, 2.5, 3.0, 3.5, 4.0],
    labels=["< 2.0", "2.0–2.5", "2.5–3.0", "3.0–3.5", "3.5–4.0"]
)

# Loan amount bands
df["loan_band"] = pd.cut(
    df["original_loan_amount"],
    bins=[0, 5000, 15000, 30000, 50000, 999999],
    labels=["< $5K", "$5K–15K", "$15K–30K", "$30K–50K", "> $50K"]
)


# =============================================================================
# SEGMENTATION HELPER
# =============================================================================
def segment(group_col, label, min_n=5):
    """Returns a DataFrame with count, default_count, default_rate per group."""
    g = (df.groupby(group_col, observed=True)["default_flag"]
           .agg(count="count", defaults="sum")
           .reset_index())
    g["default_rate"] = g["defaults"] / g["count"]
    g = g[g["count"] >= min_n].sort_values("default_rate", ascending=False)
    g.columns = [label, "n", "defaults", "default_rate"]
    return g


segs = {
    "Level":          segment("level",        "Level"),
    "Student type":   segment("student_type", "Student type"),
    "Campus":         segment("campus_code",  "Campus"),
    "GPA band":       segment("gpa_band",     "GPA band"),
    "Loan amount":    segment("loan_band",     "Loan amount"),
    "Withdrawn":      segment("withdrawn",     "Withdrawn"),
    "Graduated":      segment("graduated",     "Graduated"),
    "Program":        segment("program",       "Program", min_n=10),
}

# Print all tables
OVERALL = df["default_flag"].mean()
print(f"\n{'='*58}")
print(f"  Overall default rate: {OVERALL:.1%}  (n={len(df):,})")
print(f"{'='*58}")
for title, tbl in segs.items():
    print(f"\n── {title} {'─'*(50-len(title))}")
    for _, row in tbl.iterrows():
        val   = row.iloc[0]
        rate  = row["default_rate"]
        n     = int(row["n"])
        defs  = int(row["defaults"])
        delta = rate - OVERALL
        flag  = " ▲" if delta > 0.03 else (" ▼" if delta < -0.03 else "")
        bar   = "█" * int(rate * 100)
        print(f"  {str(val):<35} {rate:5.1%}  n={n:<5} ({defs} defaults){flag}")


# =============================================================================
# EXPORT CSV (all segments combined)
# =============================================================================
all_rows = []
for title, tbl in segs.items():
    tbl_copy = tbl.copy()
    tbl_copy.insert(0, "Segment", title)
    tbl_copy.columns = ["Segment", "Value", "n", "Defaults", "Default Rate"]
    all_rows.append(tbl_copy)

export = pd.concat(all_rows, ignore_index=True)
export["Default Rate"] = export["Default Rate"].map(lambda x: f"{x:.1%}")
export.to_csv(OUT_CSV, index=False)
print(f"\nCSV saved: {OUT_CSV}")


# =============================================================================
# VISUALIZATION — 8 panels
# =============================================================================
BLUE   = "#378ADD"
RED    = "#E24B4A"
AMBER  = "#EF9F27"
GREEN  = "#1D9E75"
GRAY   = "#888780"

def bar_colors(rates, overall=OVERALL):
    return [RED if r > overall + 0.03
            else GREEN if r < overall - 0.03
            else AMBER for r in rates]

fig = plt.figure(figsize=(18, 22))
fig.suptitle("FRIS — Default Rate Segmentation\nNew England College",
             fontsize=15, fontweight="bold", y=0.98)
gs = gridspec.GridSpec(4, 2, figure=fig, hspace=0.55, wspace=0.35)

overall_line = dict(color=GRAY, linestyle="--", linewidth=1, label=f"Overall {OVERALL:.1%}")

def add_value_labels(ax, bars, rates):
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_width() + 0.003, bar.get_y() + bar.get_height() / 2,
                f"{rate:.1%}", va="center", ha="left", fontsize=8)

# -- 1. Level --
ax = fig.add_subplot(gs[0, 0])
t = segs["Level"]
bars = ax.barh(t["Level"], t["default_rate"], color=bar_colors(t["default_rate"]), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By level", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_value_labels(ax, bars, t["default_rate"])
ax.legend(fontsize=8)

# -- 2. Student type --
ax = fig.add_subplot(gs[0, 1])
t = segs["Student type"]
bars = ax.barh(t["Student type"], t["default_rate"], color=bar_colors(t["default_rate"]), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By student type", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_value_labels(ax, bars, t["default_rate"])
ax.tick_params(axis="y", labelsize=8)

# -- 3. Campus --
ax = fig.add_subplot(gs[1, 0])
t = segs["Campus"]
bars = ax.barh(t["Campus"], t["default_rate"], color=bar_colors(t["default_rate"]), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By campus", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_value_labels(ax, bars, t["default_rate"])

# -- 4. GPA band --
ax = fig.add_subplot(gs[1, 1])
t = segs["GPA band"].sort_values("GPA band")
bars = ax.barh(t["GPA band"], t["default_rate"], color=bar_colors(t["default_rate"]), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By GPA band", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_value_labels(ax, bars, t["default_rate"])

# -- 5. Loan amount band --
ax = fig.add_subplot(gs[2, 0])
t = segs["Loan amount"]
bars = ax.barh(t["Loan amount"], t["default_rate"], color=bar_colors(t["default_rate"]), height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By original loan amount", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_value_labels(ax, bars, t["default_rate"])

# -- 6. Withdrawn / Graduated --
ax = fig.add_subplot(gs[2, 1])
labels = ["Not withdrawn", "Withdrawn", "Not graduated", "Graduated"]
rates  = [
    df[df["withdrawn"] == 0]["default_flag"].mean(),
    df[df["withdrawn"] == 1]["default_flag"].mean(),
    df[df["graduated"] == 0]["default_flag"].mean(),
    df[df["graduated"] == 1]["default_flag"].mean(),
]
colors = bar_colors(rates)
bars   = ax.barh(labels, rates, color=colors, height=0.5)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By withdrawn / graduated status", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
add_value_labels(ax, bars, rates)

# -- 7. Top 15 programs --
ax = fig.add_subplot(gs[3, :])
t = segs["Program"].head(15)
bars = ax.barh(t["Program"], t["default_rate"], color=bar_colors(t["default_rate"]), height=0.6)
ax.axvline(OVERALL, **overall_line)
ax.set_title("By program (top 15 by default rate, min n=10)", fontsize=11, fontweight="500")
ax.set_xlabel("Default rate")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
ax.tick_params(axis="y", labelsize=8)
add_value_labels(ax, bars, t["default_rate"])

# Legend
from matplotlib.patches import Patch
legend_els = [
    Patch(color=RED,   label=f"Above average (>{OVERALL+0.03:.0%})"),
    Patch(color=AMBER, label="Near average"),
    Patch(color=GREEN, label=f"Below average (<{OVERALL-0.03:.0%})"),
]
fig.legend(handles=legend_els, loc="lower center", ncol=3,
           fontsize=9, bbox_to_anchor=(0.5, 0.005))

plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
print(f"Chart saved: {OUT_PNG}")
print("=== DONE ===")