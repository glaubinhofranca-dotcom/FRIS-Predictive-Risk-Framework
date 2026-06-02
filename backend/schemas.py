"""
FRIS — Pydantic schemas for pipeline results.

These models define the contract between the Python pipeline and the frontend.
If a pipeline module changes its return structure, update the schema here first
so that broken contracts are caught at startup / in tests rather than at runtime.
"""

from pydantic import BaseModel


class EtlResult(BaseModel):
    total_raw: int
    excluded_invalid_levl: int
    valid_population: int
    levl_breakdown: dict[str, int]
    defaults: int
    default_rate: float
    default_rate_by_level: dict[str, float]
    feature_completeness: dict[str, float]
    output_path: str
    shape: list[int]
    sis_profile: str


class _MissingStats(BaseModel):
    missing_n: int
    missing_pct: float


class _ClassCount(BaseModel):
    n: int
    pct: float


class _Distribution(BaseModel):
    min: float
    max: float
    mean: float
    median: float
    std: float
    p25: float
    p75: float


class EdaResult(BaseModel):
    n_rows: int
    n_cols: int
    class_balance: dict[str, _ClassCount]
    missing_values: dict[str, _MissingStats]
    distributions: dict[str, _Distribution]
    correlations_with_default: dict[str, float]


class SegmentRow(BaseModel):
    value: str
    n: int
    defaults: int
    default_rate: float


class SegmentationResult(BaseModel):
    overall_default_rate: float
    total_students: int
    total_defaults: int
    idr_rate: float
    non_idr_rate: float
    idr_differential: float
    idr_n: int
    non_idr_n: int
    segments: dict[str, list[SegmentRow]]
    chart_path: str
    csv_path: str


class _ModelMetrics(BaseModel):
    roc_auc_mean: float
    roc_auc_std: float
    f1_mean: float
    f1_std: float
    precision_mean: float
    precision_std: float
    recall_mean: float
    recall_std: float
    accuracy_mean: float
    accuracy_std: float


class _SubgroupAuc(BaseModel):
    auc: float
    n: int
    defaults: int
    default_rate: float


class ModelResult(BaseModel):
    best_model: str
    cv_folds: int
    best_auc: float
    model_results: dict[str, _ModelMetrics]
    feature_importance: dict[str, float]
    subgroup_auc: dict[str, _SubgroupAuc]
    training_rows: int
    class_balance: dict[str, int]
    chart_path: str
    model_path: str
