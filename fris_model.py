"""
FRIS v1 -- Machine Learning Model
New England College -- Student Financial Services

PURPOSE:
    Trains and evaluates financial risk prediction models on the
    real NEC student dataset produced by fris_etl.py.

INPUT:  dataset_fris.csv
OUTPUT: model_results_fris.png
        best_model_fris.pkl  (saved model for future predictions)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import classification_report, roc_auc_score

SCRIPT_DIR   = Path(__file__).parent
DATA_FILE    = SCRIPT_DIR / "dataset_fris.csv"
OUTPUT_PNG   = SCRIPT_DIR / "model_results_fris.png"
MODEL_FILE   = SCRIPT_DIR / "best_model_fris.pkl"
CV_FOLDS     = 5
RANDOM_STATE = 42


# =============================================================================
# LOAD DATA
# =============================================================================
print("=== LOADING DATA ===")
data = pd.read_csv(DATA_FILE, low_memory=False)
print(f"  Rows: {len(data):,}  |  Columns: {len(data.columns)}")
print(f"  Default rate: {data['default_flag'].mean():.1%}  "
      f"({data['default_flag'].sum():,} defaults of {len(data):,} students)")


# =============================================================================
# FEATURE SELECTION
# =============================================================================
# Categorical features (will be one-hot encoded)
CAT_FEATURES = [col for col in [
    "level",
    "program",
    "student_type",
    "campus_code",
    "on_payment_plan",
] if col in data.columns]

# Numeric features (will be imputed with median then scaled)
NUM_FEATURES = [col for col in [
    "gpa",
    "graduated",
    "withdrawn",
    "num_loans",
    "original_loan_amount",
    "current_balance",      # WARNING: partial leakage risk — current_balance
                            # decreases as students repay, so it partially reflects
                            # repayment behavior correlated with default status.
                            # Useful for retrospective analysis; review before
                            # deploying for prospective prediction on new students.
    "credits_earned",
] if col in data.columns]

# NOTE: "major" excluded from default run due to high cardinality.
#       Include it after confirming with Kristen (adds noise if too many categories).
#       Uncomment below to include:
# if "major" in data.columns and data["major"].nunique() < 50:
#     CAT_FEATURES.append("major")

ALL_FEATURES = CAT_FEATURES + NUM_FEATURES
TARGET = "default_flag"

print(f"\n  Categorical features ({len(CAT_FEATURES)}): {CAT_FEATURES}")
print(f"  Numeric features    ({len(NUM_FEATURES)}): {NUM_FEATURES}")

# Drop rows where target is null
data = data.dropna(subset=[TARGET])
X = data[ALL_FEATURES]
y = data[TARGET]

print(f"\n  Training set: {len(X):,} rows after dropping null targets")
print(f"  Class balance: {y.value_counts().to_dict()}")



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
# class_weight="balanced" handles class imbalance automatically
# (avoids predicting all non-default when default rate is low)
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
    cv_res = cross_validate(model, X, y, cv=cv, scoring=scoring)
    results[name] = {k.replace("test_", ""): v for k, v in cv_res.items() if k.startswith("test_")}
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
print("\n=== TRAINING BEST MODEL (full dataset) ===")
best_model = models[best_name]
best_model.fit(X, y)

# Save model for future predictions
joblib.dump(best_model, MODEL_FILE)
print(f"  Model saved: {MODEL_FILE}")


# =============================================================================
# FEATURE IMPORTANCE
# =============================================================================
print("\n=== TOP 15 FEATURES ===")
clf = best_model.named_steps["clf"]
prep = best_model.named_steps["prep"]

# Reconstruct feature names after one-hot encoding
num_names = NUM_FEATURES
cat_names = list(prep.named_transformers_["cat"]
                     .named_steps["encoder"]
                     .get_feature_names_out(CAT_FEATURES))
feature_names = num_names + cat_names

if hasattr(clf, "feature_importances_"):
    imp = pd.Series(clf.feature_importances_, index=feature_names).sort_values(ascending=False)
elif hasattr(clf, "coef_"):
    imp = pd.Series(np.abs(clf.coef_[0]), index=feature_names).sort_values(ascending=False)

for feat, val in imp.head(15).items():
    bar = "█" * int(val / imp.iloc[0] * 40)
    print(f"  {feat:<40} {val:.4f}  {bar}")


# =============================================================================
# VISUALIZATION
# =============================================================================
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("FRIS v2 -- Model Evaluation (Real NEC Data)", fontsize=13, fontweight="bold")

# Left: AUC boxplot across models
ax = axes[0]
auc_data = [results[n]["roc_auc"] for n in models]
bp = ax.boxplot(auc_data, labels=list(models.keys()), patch_artist=True)
colors = ["#378ADD", "#E24B4A", "#1D9E75"]
for patch, color in zip(bp["boxes"], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.75)
ax.set_ylabel("AUC (ROC)")
ax.set_title(f"AUC by model -- {CV_FOLDS}-fold stratified CV")
ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5, label="random baseline")
ax.legend(fontsize=9)
ax.set_ylim(0.4, 1.05)
ax.tick_params(axis="x", labelsize=9)

# Add mean AUC annotation on each box
for i, name in enumerate(models.keys()):
    mean_auc = results[name]["roc_auc"].mean()
    ax.text(i + 1, mean_auc + 0.01, f"{mean_auc:.3f}",
            ha="center", va="bottom", fontsize=9, fontweight="bold")

# Right: top 15 feature importances
ax2 = axes[1]
top15 = imp.head(15)
bars = ax2.barh(top15.index[::-1], top15.values[::-1], color="#378ADD", alpha=0.8)
ax2.set_xlabel("Importance")
ax2.set_title(f"Top 15 features -- {best_name}")
ax2.tick_params(axis="y", labelsize=8)
for bar, val in zip(bars, top15.values[::-1]):
    ax2.text(bar.get_width() + imp.iloc[0] * 0.01,
             bar.get_y() + bar.get_height() / 2,
             f"{val:.3f}", va="center", fontsize=7)

plt.tight_layout()
plt.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
print(f"\n  Chart saved: {OUTPUT_PNG}")
print("\n=== DONE ===")