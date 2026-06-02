"""
FRIS — Shared configuration constants.

All tunable thresholds, hyperparameters, and style values live here so they
have a single source of truth across ETL, segmentation, model, and frontend.
"""

# ── Pipeline thresholds ────────────────────────────────────────────────────────
DEFAULT_DAYS_THRESHOLD = 270   # 34 CFR § 682.200 — federal loan default definition
BAR_SCALE = 5                  # chars per percentage point in progress bars

# ── Cross-validation ──────────────────────────────────────────────────────────
CV_FOLDS = 5
RANDOM_STATE = 42
LEVEL_CODES = ["UG", "GR"]

# ── Segmentation thresholds ───────────────────────────────────────────────────
MIN_N_DEFAULT = 5
MIN_N_PROGRAM = 10

# IDR detection — Banner stores full plan names, not short codes.
# Matching on substrings covers all IBR, PAYE, REPAYE, SAVE, ICR variants.
IDR_PATTERN = (
    r"income.based repayment"
    r"|pay as you earn"
    r"|revised pay as you earn"
    r"|income contingent"
    r"|saving on a valuable education"
)

# ── Color palette (shared between Python visualizations) ──────────────────────
COLORS = {
    "blue":       "#378ADD",
    "blue_dark":  "#185FA5",
    "red":        "#E24B4A",
    "amber":      "#EF9F27",
    "green":      "#1D9E75",
    "gray":       "#888780",
    "gray_light": "#B4B2A9",
    "text_muted": "#5F5E5A",
}

# ── Model hyperparameters ─────────────────────────────────────────────────────
MODEL_HYPERPARAMS = {
    "Random Forest": {
        "n_estimators": 300,
        "max_depth": 8,
    },
    "Gradient Boosting": {
        "n_estimators": 300,
        "max_depth": 4,
        "learning_rate": 0.05,
    },
}
