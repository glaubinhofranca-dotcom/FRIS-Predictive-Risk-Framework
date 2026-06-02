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

import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib

from pathlib import Path
from matplotlib.patches import Patch
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate, cross_val_predict
from sklearn.metrics import roc_auc_score
from sklearn.exceptions import ConvergenceWarning

from fris_config import CV_FOLDS, RANDOM_STATE, LEVEL_CODES, COLORS, MODEL_HYPERPARAMS

SCRIPT_DIR = Path(__file__).parent


# ── Model construction ─────────────────────────────────────────────────────────

def _build_models(preprocessor) -> dict:
    rf = MODEL_HYPERPARAMS["Random Forest"]
    gb = MODEL_HYPERPARAMS["Gradient Boosting"]
    return {
        "Logistic Regression": Pipeline([
            ("prep", preprocessor),
            ("clf", LogisticRegression(
                class_weight="balanced",
                max_iter=1000,
                random_state=RANDOM_STATE,
            )),
        ]),
        "Random Forest": Pipeline([
            ("prep", preprocessor),
            ("clf", RandomForestClassifier(
                n_estimators=rf["n_estimators"],
                max_depth=rf["max_depth"],
                class_weight="balanced",
                random_state=RANDOM_STATE,
            )),
        ]),
        "Gradient Boosting": Pipeline([
            ("prep", preprocessor),
            ("clf", GradientBoostingClassifier(
                n_estimators=gb["n_estimators"],
                max_depth=gb["max_depth"],
                learning_rate=gb["learning_rate"],
                random_state=RANDOM_STATE,
            )),
        ]),
    }


# ── Private pipeline steps ─────────────────────────────────────────────────────

def _load_features(data_path: Path):
    """Load CSV and return (data, X, y, cat_features, num_features)."""
    print("=== LOADING DATA ===")
    data = pd.read_csv(data_path, low_memory=False)
    print(f"  Rows: {len(data):,}  |  Columns: {len(data.columns)}")
    print(f"  Default rate: {data['default_flag'].mean():.1%}  "
          f"({data['default_flag'].sum():,} of {len(data):,})")
    print(f"\n  Level distribution (LEVL_CODE from Banner):")
    print(data["level"].value_counts().to_string())

    cat_features = [col for col in [
        "level", "program", "student_type", "campus_code", "payment_plan",
    ] if col in data.columns]

    # NOTE: current_balance has partial leakage risk — reflects repayment behavior.
    # Valid for retrospective analysis. Review before prospective scoring.
    num_features = [col for col in [
        "gpa", "graduated", "withdrawn", "credits_earned",
        "num_loans", "original_loan_amount", "current_balance",
    ] if col in data.columns]

    print(f"\n  Categorical features ({len(cat_features)}): {cat_features}")
    print(f"  Numeric features    ({len(num_features)}): {num_features}")

    data = data.dropna(subset=["default_flag"])
    X = data[cat_features + num_features]
    y = data["default_flag"]
    print(f"\n  Training rows: {len(X):,} | Class balance: {y.value_counts().to_dict()}")

    return data, X, y, cat_features, num_features


def _build_preprocessor(num_features: list, cat_features: list) -> ColumnTransformer:
    """Build ColumnTransformer with imputation + scaling/encoding."""
    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer([
        ("num", numeric_transformer, num_features),
        ("cat", categorical_transformer, cat_features),
    ])


def _cross_validate_models(models: dict, X, y, cv) -> dict:
    """Run stratified CV for each model and return per-metric score arrays."""
    scoring = ["roc_auc", "f1", "precision", "recall", "accuracy"]
    cv_results: dict[str, dict] = {}
    for name, model in models.items():
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ConvergenceWarning)
            raw = cross_validate(model, X, y, cv=cv, scoring=scoring)
        cv_results[name] = {k.replace("test_", ""): v for k, v in raw.items()
                            if k.startswith("test_")}
        r = cv_results[name]
        print(f"{'─'*44}")
        print(f"  {name}")
        print(f"  AUC:       {r['roc_auc'].mean():.3f} ± {r['roc_auc'].std():.3f}")
        print(f"  F1:        {r['f1'].mean():.3f} ± {r['f1'].std():.3f}")
        print(f"  Precision: {r['precision'].mean():.3f} ± {r['precision'].std():.3f}")
        print(f"  Recall:    {r['recall'].mean():.3f} ± {r['recall'].std():.3f}")
        print(f"  Accuracy:  {r['accuracy'].mean():.3f} ± {r['accuracy'].std():.3f}")
    return cv_results


def _retrain_best(models: dict, best_name: str, X, y):
    """Retrain the best model on the full dataset and return the fitted model."""
    best_model = models[best_name]
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        best_model.fit(X, y)
    return best_model


def _feature_importance(best_model, num_features: list, cat_features: list):
    """
    Extract raw importances and aggregate them back to pre-OHE feature names.

    Returns (imp_series, agg_series) both sorted descending.
    """
    clf = best_model.named_steps["clf"]
    prep = best_model.named_steps["prep"]

    cat_names = list(
        prep.named_transformers_["cat"]
        .named_steps["encoder"]
        .get_feature_names_out(cat_features)
    )
    feature_names = num_features + cat_names

    if hasattr(clf, "feature_importances_"):
        imp = pd.Series(clf.feature_importances_, index=feature_names).sort_values(ascending=False)
    elif hasattr(clf, "coef_"):
        imp = pd.Series(np.abs(clf.coef_[0]), index=feature_names).sort_values(ascending=False)
    else:
        raise ValueError(
            f"Classifier {type(clf).__name__} has no interpretable feature importances."
        )

    agg: dict[str, float] = {}
    for feat, val in imp.items():
        root = next((c for c in cat_features if feat.startswith(c + "_")), None)
        if root is None and feat in num_features:
            root = feat
        if root:
            agg[root] = agg.get(root, 0) + float(val)

    agg_series = pd.Series(agg).sort_values(ascending=False)
    return imp, agg_series


def _compute_subgroup_auc(best_model, X, y, data, cv) -> dict:
    """Compute OOF AUC per LEVL_CODE subgroup via cross_val_predict."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        oof_proba = cross_val_predict(
            best_model, X, y, cv=cv, method="predict_proba"
        )[:, 1]

    subgroup_auc: dict[str, dict] = {}
    for code in LEVEL_CODES:
        mask = (data.loc[data.index.isin(X.index), "level"] == code).values
        if mask.sum() < 10:
            print(f"  {code}: skipped (n={mask.sum()} — too few samples)")
            continue
        sub_y = y.values[mask]
        sub_proba = oof_proba[mask]
        n = int(mask.sum())
        d = int(sub_y.sum())
        if len(np.unique(sub_y)) < 2:
            print(f"  {code}: n={n:,} | defaults={d} — only one class, AUC undefined")
            continue
        auc = float(roc_auc_score(sub_y, sub_proba))
        subgroup_auc[code] = {
            "auc": round(auc, 4),
            "n": n,
            "defaults": d,
            "default_rate": round(d / n, 4),
        }
        print(f"  {code}: AUC={auc:.3f} | n={n:,} | defaults={d} ({d/n:.1%})")

    return subgroup_auc


def _plot_results(cv_results: dict, best_name: str, agg_series: pd.Series,
                  output_png: Path) -> None:
    """Render model benchmark + feature importance chart and save to output_png."""
    C = COLORS
    names = list(cv_results.keys())
    means = [cv_results[n]["roc_auc"].mean() for n in names]
    stds = [cv_results[n]["roc_auc"].std() for n in names]
    bar_colors = [C["blue"] if n == best_name else C["gray_light"] for n in names]
    edge_colors = [C["blue_dark"] if n == best_name else C["gray"] for n in names]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    fig.suptitle(
        "FRIS v3 — Model Evaluation (LEVL_CODE level)",
        fontsize=12, fontweight="bold",
    )

    ax = axes[0]
    x_pos = np.arange(len(names))
    ax.bar(x_pos, means, color=bar_colors, edgecolor=edge_colors, linewidth=1.5, width=0.45)
    ax.errorbar(x_pos, means, yerr=stds, fmt="none", ecolor=C["text_muted"],
                elinewidth=1.5, capsize=6, capthick=1.5)

    for i, (m, s) in enumerate(zip(means, stds)):
        suffix = "  ✓ selected" if names[i] == best_name else ""
        color = C["blue_dark"] if names[i] == best_name else C["text_muted"]
        ax.text(x_pos[i], m + s + 0.006, f"{m:.3f}{suffix}",
                ha="center", va="bottom", fontsize=10,
                color=color, fontweight="bold" if names[i] == best_name else "normal")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(names, fontsize=10)
    ax.set_ylim(0.60, 0.85)
    ax.set_yticks([0.60, 0.65, 0.70, 0.75, 0.80])
    ax.set_ylabel("AUC-ROC")
    ax.set_title(f"Model benchmarking · {CV_FOLDS}-fold stratified CV")
    ax.axhline(0.5, color=C["gray_light"], linestyle="--", alpha=0.5, linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)

    ax2 = axes[1]
    top = agg_series.head(10)
    academic = {"gpa", "graduated", "credits_earned", "withdrawn", "level"}
    loan_fin = {"num_loans", "original_loan_amount", "current_balance"}
    feat_colors = [
        C["blue"] if f in academic else C["green"] if f in loan_fin else C["gray_light"]
        for f in top.index
    ]

    bars2 = ax2.barh(top.index[::-1], top.values[::-1],
                     color=feat_colors[::-1], height=0.55)
    ax2.set_xlabel("Feature importance (aggregated)")
    ax2.set_title(f"Top 10 features · {best_name}\n(LEVL_CODE → 'level' column)")
    ax2.spines[["top", "right", "bottom"]].set_visible(False)
    ax2.grid(axis="x", alpha=0.25)

    for bar, val in zip(bars2, top.values[::-1]):
        ax2.text(bar.get_width() + agg_series.iloc[0] * 0.01,
                 bar.get_y() + bar.get_height() / 2,
                 f"{val * 100:.1f}%", va="center", fontsize=8)

    ax2.legend(handles=[
        Patch(color=C["blue"],       label="Academic / enrollment"),
        Patch(color=C["green"],      label="Loan / financial"),
        Patch(color=C["gray_light"], label="Institutional / contextual"),
    ], loc="lower right", fontsize=8)

    plt.tight_layout()
    plt.savefig(output_png, dpi=150, bbox_inches="tight")
    plt.close("all")


# ── Public entry point ─────────────────────────────────────────────────────────

def run_model(data_path: Path, session_dir: Path) -> dict:
    """
    Train and evaluate all models, save best model and chart.

    Parameters
    ----------
    data_path : Path
        Path to dataset_fris.csv produced by run_etl().
    session_dir : Path
        Directory for output files (PNG + PKL).

    Returns
    -------
    dict
        Model metrics for the API / dashboard.
    """
    session_dir = Path(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    output_png = session_dir / "fris_model_results.png"
    model_file = session_dir / "fris_best_model.pkl"

    data, X, y, cat_features, num_features = _load_features(data_path)
    preprocessor = _build_preprocessor(num_features, cat_features)
    models = _build_models(preprocessor)

    print(f"\n=== CROSS-VALIDATION ({CV_FOLDS}-fold stratified) ===\n")
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    cv_results = _cross_validate_models(models, X, y, cv)

    best_name = max(cv_results, key=lambda n: cv_results[n]["roc_auc"].mean())
    print(f"\n  Best model by AUC: {best_name}")

    print(f"\n=== TRAINING BEST MODEL ({best_name}) — full dataset ===")
    best_model = _retrain_best(models, best_name, X, y)
    joblib.dump(best_model, model_file)
    print(f"  Saved: {model_file}")

    print("\n=== TOP 15 FEATURES ===")
    imp, agg_series = _feature_importance(best_model, num_features, cat_features)
    for feat, val in imp.head(15).items():
        bar = "█" * int(val / imp.iloc[0] * 40)
        print(f"  {feat:<42} {val:.4f}  {bar}")
    print("\n  Aggregated importance by feature (pre-OHE):")
    for feat, val in agg_series.items():
        bar = "█" * int(val / agg_series.iloc[0] * 40)
        print(f"  {feat:<25} {val:.4f}  ({val * 100:.1f}%)  {bar}")

    print("\n=== SUB-GROUP AUC BY LEVL_CODE ===")
    subgroup_auc = _compute_subgroup_auc(best_model, X, y, data, cv)

    _plot_results(cv_results, best_name, agg_series, output_png)
    print(f"\n  Chart saved: {output_png}")
    print("=== DONE ===")

    model_results_out = {
        name: {
            "roc_auc_mean":    round(float(r["roc_auc"].mean()), 4),
            "roc_auc_std":     round(float(r["roc_auc"].std()), 4),
            "f1_mean":         round(float(r["f1"].mean()), 4),
            "f1_std":          round(float(r["f1"].std()), 4),
            "precision_mean":  round(float(r["precision"].mean()), 4),
            "precision_std":   round(float(r["precision"].std()), 4),
            "recall_mean":     round(float(r["recall"].mean()), 4),
            "recall_std":      round(float(r["recall"].std()), 4),
            "accuracy_mean":   round(float(r["accuracy"].mean()), 4),
            "accuracy_std":    round(float(r["accuracy"].std()), 4),
        }
        for name, r in cv_results.items()
    }

    class_vc = y.value_counts()
    return {
        "best_model": best_name,
        "cv_folds": CV_FOLDS,
        "best_auc": round(float(cv_results[best_name]["roc_auc"].mean()), 4),
        "model_results": model_results_out,
        "feature_importance": {k: round(v, 4) for k, v in agg_series.to_dict().items()},
        "subgroup_auc": subgroup_auc,
        "training_rows": int(len(X)),
        "class_balance": {str(k): int(v) for k, v in class_vc.items()},
        "chart_path": str(output_png),
        "model_path": str(model_file),
    }


if __name__ == "__main__":
    result = run_model(
        data_path=SCRIPT_DIR / "dataset_fris.csv",
        session_dir=SCRIPT_DIR,
    )
    print(f"\n  Best model: {result['best_model']}  AUC={result['best_auc']:.3f}")
