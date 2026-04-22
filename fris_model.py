"""
FRIS v3 — Machine Learning Model
New England College · Student Financial Services

CHANGE FROM v2:
    The 'level' feature now reflects LEVL_CODE from Banner (set by fris_etl.py).
    Sub-group AUC analysis is split by LEVL_CODE values (UG, GR)
    rather than by ID prefix pattern matching.

INPUT:  dataset_fris.csv   (produced by fris_etl.py)
OUTPUT: fris_model_results.png
        fris_best_model.pkl
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate, cross_val_predict
from sklearn.metrics import roc_auc_score

SCRIPT_DIR   = Path(__file__).parent
DATA_FILE    = SCRIPT_DIR / "dataset_fris.csv"
OUTPUT_PNG   = SCRIPT_DIR / "fris_model_results.png"
MODEL_FILE   = SCRIPT_DIR / "fris_best_model.pkl"
CV_FOLDS     = 5
RANDOM_STATE = 42

# Banner LEVL_CODE values used for sub-group analysis
LEVEL_CODES = ["UG", "GR"]


# =============================================================================
# LOAD
# =============================================================================
print("=== LOADING DATA ===")
data = pd.read_csv(DATA_FILE, low_memory=False)
print(f"  Rows: {len(data):,}  |  Columns: {len(data.columns)}")
print(f"  Default rate: {data['default_flag'].mean():.1%}  "
      f"({data['default_flag'].sum():,} of {len(data):,})")
print(f"\n  Level distribution (LEVL_CODE from Banner):")
print(data["level"].value_counts().to_string())


# =============================================================================
# FEATURE SELECTION
# =============================================================================
# Categorical — one-hot encoded
# 'level' encodes LEVL_CODE: UG (undergraduate), GR (graduate)
CAT_FEATURES = [col for col in [
    "level",          # LEVL_CODE — Banner authoritative academic level
    "program",
    "student_type",
    "campus_code",
    "payment_plan",
] if col in data.columns]

# Numeric — median-imputed, standard-scaled
NUM_FEATURES = [col for col in [
    "gpa",
    "graduated",
    "withdrawn",
    "credits_earned",
    "num_loans",
    "original_loan_amount",
    "current_balance",   # NOTE: partial leakage risk — reflects repayment behavior.
                         # Valid for retrospective analysis. Review before using for
                         # prospective scoring on students with no repayment history.
] if col in data.columns]

# NOTE: 'major' excluded by default (high cardinality, often redundant with 'program').
# Uncomment to include if fewer than 50 unique values:
# if "major" in data.columns and data["major"].nunique() < 50:
#     CAT_FEATURES.append("major")

ALL_FEATURES = CAT_FEATURES + NUM_FEATURES
TARGET       = "default_flag"

print(f"\n  Categorical features ({len(CAT_FEATURES)}): {CAT_FEATURES}")
print(f"  Numeric features    ({len(NUM_FEATURES)}): {NUM_FEATURES}")

data = data.dropna(subset=[TARGET])
X    = data[ALL_FEATURES]
y    = data[TARGET]

print(f"\n  Training rows: {len(X):,} | Class balance: {y.value_counts().to_dict()}")


# =============================================================================
# PREPROCESSING PIPELINE
# =============================================================================
numeric_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler",  StandardScaler()),
])

categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
    ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
])

preprocessor = ColumnTransformer([
    ("num", numeric_transformer, NUM_FEATURES),
    ("cat", categorical_transformer, CAT_FEATURES),
])


# =============================================================================
# MODELS
# class_weight="balanced" compensates for 7.5% minority class
# =============================================================================
models = {
    "Logistic Regression": Pipeline([
        ("prep", preprocessor),
        ("clf",  LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=RANDOM_STATE
        )),
    ]),
    "Random Forest": Pipeline([
        ("prep", preprocessor),
        ("clf",  RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            class_weight="balanced",
            random_state=RANDOM_STATE
        )),
    ]),
    "Gradient Boosting": Pipeline([
        ("prep", preprocessor),
        ("clf",  GradientBoostingClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            random_state=RANDOM_STATE
        )),
    ]),
}


# =============================================================================
# STRATIFIED CROSS-VALIDATION
# =============================================================================
print(f"\n=== CROSS-VALIDATION ({CV_FOLDS}-fold stratified) ===\n")
cv      = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
scoring = ["roc_auc", "f1", "precision", "recall", "accuracy"]
results = {}

for name, model in models.items():
    cv_res  = cross_validate(model, X, y, cv=cv, scoring=scoring)
    results[name] = {k.replace("test_", ""): v for k, v in cv_res.items()
                     if k.startswith("test_")}
    r = results[name]
    print(f"{'─'*44}")
    print(f"  {name}")
    print(f"  AUC:       {r['roc_auc'].mean():.3f} ± {r['roc_auc'].std():.3f}")
    print(f"  F1:        {r['f1'].mean():.3f} ± {r['f1'].std():.3f}")
    print(f"  Precision: {r['precision'].mean():.3f} ± {r['precision'].std():.3f}")
    print(f"  Recall:    {r['recall'].mean():.3f} ± {r['recall'].std():.3f}")
    print(f"  Accuracy:  {r['accuracy'].mean():.3f} ± {r['accuracy'].std():.3f}")

best_name = max(results, key=lambda n: results[n]["roc_auc"].mean())
print(f"\n  Best model by AUC: {best_name}")


# =============================================================================
# RETRAIN BEST MODEL ON FULL DATASET
# =============================================================================
print(f"\n=== TRAINING BEST MODEL ({best_name}) — full dataset ===")
best_model = models[best_name]
best_model.fit(X, y)
joblib.dump(best_model, MODEL_FILE)
print(f"  Saved: {MODEL_FILE}")


# =============================================================================
# FEATURE IMPORTANCE
# =============================================================================
print("\n=== TOP 15 FEATURES ===")
clf  = best_model.named_steps["clf"]
prep = best_model.named_steps["prep"]

num_names = NUM_FEATURES
cat_names = list(
    prep.named_transformers_["cat"]
        .named_steps["encoder"]
        .get_feature_names_out(CAT_FEATURES)
)
feature_names = num_names + cat_names

if hasattr(clf, "feature_importances_"):
    imp = pd.Series(clf.feature_importances_, index=feature_names).sort_values(ascending=False)
elif hasattr(clf, "coef_"):
    imp = pd.Series(np.abs(clf.coef_[0]), index=feature_names).sort_values(ascending=False)

for feat, val in imp.head(15).items():
    bar = "█" * int(val / imp.iloc[0] * 40)
    print(f"  {feat:<42} {val:.4f}  {bar}")

# Aggregate importance by original feature group (before one-hot expansion)
print("\n  Aggregated importance by feature (pre-OHE):")
agg = {}
for feat, val in imp.items():
    # match cat feature names like "level_UG", "program_BSN Nursing", etc.
    root = next((c for c in CAT_FEATURES if feat.startswith(c + "_")), None)
    if root is None and feat in NUM_FEATURES:
        root = feat
    if root:
        agg[root] = agg.get(root, 0) + val

agg_series = pd.Series(agg).sort_values(ascending=False)
for feat, val in agg_series.items():
    bar = "█" * int(val / agg_series.iloc[0] * 40)
    print(f"  {feat:<25} {val:.4f}  ({val * 100:.1f}%)  {bar}")


# =============================================================================
# SUB-GROUP AUC BY LEVL_CODE
# =============================================================================
print("\n=== SUB-GROUP AUC BY LEVL_CODE (Banner academic level) ===")
# Use out-of-fold predictions so there is no data leakage in the sub-group scores
oof_proba = cross_val_predict(
    best_model, X, y, cv=cv, method="predict_proba"
)[:, 1]

for code in LEVEL_CODES:
    mask = data.loc[data.index.isin(X.index), "level"] == code
    mask = mask.values
    if mask.sum() < 10:
        print(f"  {code}: skipped (n={mask.sum()} — too few samples)")
        continue
    sub_y     = y.values[mask]
    sub_proba = oof_proba[mask]
    n         = mask.sum()
    d         = sub_y.sum()
    if len(np.unique(sub_y)) < 2:
        print(f"  {code}: n={n:,} | defaults={d} — only one class, AUC undefined")
        continue
    auc = roc_auc_score(sub_y, sub_proba)
    print(f"  {code}: AUC={auc:.3f} | n={n:,} | defaults={d} ({d/n:.1%})")


# =============================================================================
# VISUALIZATION
# =============================================================================
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
fig.suptitle(f"FRIS v3 — Model Evaluation (1,302 NEC Borrowers · LEVL_CODE level)",
             fontsize=12, fontweight="bold")

# Left: AUC comparison
ax = axes[0]
names   = list(models.keys())
means   = [results[n]["roc_auc"].mean() for n in names]
stds    = [results[n]["roc_auc"].std()  for n in names]
colors  = ["#B4B2A9", "#378ADD", "#B4B2A9"]  # highlight Random Forest
x_pos   = np.arange(len(names))

bars = ax.bar(x_pos, means, color=colors, edgecolor=["#888780", "#185FA5", "#888780"],
              linewidth=1.5, width=0.45)
ax.errorbar(x_pos, means, yerr=stds, fmt="none", ecolor="#5F5E5A",
            elinewidth=1.5, capsize=6, capthick=1.5)

for i, (m, s) in enumerate(zip(means, stds)):
    suffix = "  ✓ selected" if names[i] == best_name else ""
    color  = "#185FA5" if names[i] == best_name else "#5F5E5A"
    ax.text(x_pos[i], m + s + 0.006, f"{m:.3f}{suffix}",
            ha="center", va="bottom", fontsize=10,
            color=color, fontweight="bold" if names[i] == best_name else "normal")

ax.set_xticks(x_pos)
ax.set_xticklabels(names, fontsize=10)
ax.set_ylim(0.60, 0.85)
ax.set_yticks([0.60, 0.65, 0.70, 0.75, 0.80])
ax.set_ylabel("AUC-ROC")
ax.set_title(f"Model benchmarking · {CV_FOLDS}-fold stratified CV")
ax.axhline(0.5, color="#B4B2A9", linestyle="--", alpha=0.5, linewidth=0.8)
ax.spines[["top", "right", "left"]].set_visible(False)
ax.grid(axis="y", alpha=0.25)

# Right: aggregated feature importance
ax2 = axes[1]
top = agg_series.head(10)
bar_colors_feat = []
academic = {"gpa", "graduated", "credits_earned", "withdrawn", "level"}
loan_fin = {"num_loans", "original_loan_amount", "current_balance"}
for f in top.index:
    if f in academic:
        bar_colors_feat.append("#378ADD")
    elif f in loan_fin:
        bar_colors_feat.append("#1D9E75")
    else:
        bar_colors_feat.append("#B4B2A9")

bars2 = ax2.barh(top.index[::-1], top.values[::-1],
                 color=bar_colors_feat[::-1], height=0.55)
ax2.set_xlabel("Feature importance (aggregated)")
ax2.set_title(f"Top 10 features · {best_name}\n(LEVL_CODE → 'level' column)")
ax2.spines[["top", "right", "bottom"]].set_visible(False)
ax2.grid(axis="x", alpha=0.25)

for bar, val in zip(bars2, top.values[::-1]):
    ax2.text(bar.get_width() + agg_series.iloc[0] * 0.01,
             bar.get_y() + bar.get_height() / 2,
             f"{val * 100:.1f}%", va="center", fontsize=8)

# Legend
from matplotlib.patches import Patch
ax2.legend(handles=[
    Patch(color="#378ADD", label="Academic / enrollment"),
    Patch(color="#1D9E75", label="Loan / financial"),
    Patch(color="#B4B2A9", label="Institutional / contextual"),
], loc="lower right", fontsize=8)

plt.tight_layout()
plt.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
print(f"\n  Chart saved: {OUTPUT_PNG}")
print("=== DONE ===")
