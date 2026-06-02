---
title: FRIS v3 Financial Risk Intelligence System
emoji: 📊
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: Predictive analytics for student loan default risk
---

# FRIS — Financial Risk Intelligence System

**Predictive Analytics for Student Loan Default Risk**
New England College · Student Financial Services

---

## Executive Summary

The **Financial Risk Intelligence System (FRIS)** is a machine learning framework designed to **predict student federal loan default risk** using institutional data.

Built on a dataset of **1,302 borrowers**, FRIS enables early identification of at-risk students, allowing institutions to intervene **before delinquency escalates to default (270+ days)**.

This system moves beyond reactive monitoring toward **proactive, data-driven financial risk prevention** in higher education.

---

## System Architecture

```
Upload file → ETL → EDA → Segmentation → Model → Dashboard
```

### Pipeline modules

| File | Responsibility |
|---|---|
| `fris_config.py` | Single source of truth for all thresholds, hyperparameters, and color palette |
| `fris_utils.py` | Shared data-cleaning helpers (`normalize_str`, `clean_currency`, etc.) |
| `fris_sis_profiles.py` | SIS adapter definitions (Banner, Workday, PeopleSoft, Colleague) |
| `fris_etl.py` | Load, apply SIS profile, filter, engineer features, output `dataset_fris.csv` |
| `fris_eda.py` | Distributions, missing values, correlations with default flag |
| `fris_segmentation.py` | Default rate by 8 dimensions + IDR policy finding |
| `fris_model.py` | 5-fold CV across 3 classifiers, feature importance, subgroup AUC |

### Web application

| Path | Responsibility |
|---|---|
| `backend/main.py` | FastAPI routes: upload, SSE stream, results, chart serving |
| `backend/pipeline.py` | Async orchestrator — runs pipeline steps via `ThreadPoolExecutor`, streams SSE events |
| `backend/schemas.py` | Pydantic models for pipeline results (`EtlResult`, `ModelResult`, etc.) |
| `frontend/index.html` | Single-page dashboard |
| `frontend/js/app.js` | File upload, SSE listener, Chart.js rendering |
| `frontend/css/dashboard.css` | Responsive styling |

---

## Multi-SIS Support

FRIS supports four Student Information Systems out of the box. Select the profile when uploading — the pipeline handles column renaming automatically; all downstream code works exclusively with internal canonical names.

| Profile key | System | Notes |
|---|---|---|
| `banner` | Banner / Ellucian | Default. Used by ~1,200 US institutions including NEC |
| `workday` | Workday Student | Column names from Workday report builder |
| `peoplesoft` | PeopleSoft / Oracle | Column names from PS Query / SQR exports |
| `colleague` | Colleague / Ellucian | Used by ~700 US institutions |

To add a new SIS, add an entry to `fris_sis_profiles.py` — no other file needs to change.

---

## Getting Started

### Run with Docker (recommended)

```bash
docker compose up --build
# Open http://localhost:7860
```

### Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 7860
# Open http://localhost:7860
```

### Run tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Run the pipeline from the CLI

```bash
python fris_etl.py          # produces dataset_fris.csv
python fris_eda.py          # prints distribution stats
python fris_segmentation.py # produces fris_segmentation.png + .csv
python fris_model.py        # produces fris_model_results.png + .pkl
```

---

## Dataset Overview

> Numbers below are from the NEC production run (2024). Your institution's results will differ.

* Total borrowers: **1,302**
* Default rate: **7.5% (98 defaults)**
* Undergraduate: **992 (76.2%)**
* Graduate: **310 (23.8%)**

Default rate by level:

* Undergraduate: **8.5%**
* Graduate: **4.5%**

All features achieved **100% completeness**, ensuring high-quality model training.

---

## Problem Statement

Student loan default creates systemic risks:

* Financial hardship for borrowers
* Increased institutional Cohort Default Rates (CDR)
* Regulatory exposure (Title IV eligibility)

Most institutions act **after delinquency occurs** — FRIS addresses this gap.

---

## Solution

FRIS provides a **predictive and actionable framework** that:

* Identifies high-risk borrowers early
* Quantifies default probability
* Enables targeted intervention strategies

---

## Methodology

### Target Definition

Default is defined as:

```
Days Delinquent > 270
```

Aligned with federal regulation (34 CFR § 682.200).

### Feature Engineering

**Academic & Enrollment**

* GPA
* Credits earned
* Graduation status
* Withdrawal indicators
* Academic level (LEVL\_CODE — Banner authoritative field)
* Program and student type

**Financial & Loan Data**

* Number of loans
* Original loan amount
* Current balance ⚠️ *partial leakage risk for prospective scoring — see `fris_config.py`*
* Payment plan

### Modeling Approach

* 5-fold Stratified Cross-Validation
* Class imbalance handled with `class_weight="balanced"`
* Models evaluated:
  * Logistic Regression
  * Random Forest
  * Gradient Boosting

Hyperparameters and CV settings are centralized in `fris_config.py`.

---

## Model Performance

> NEC run — Random Forest selected as best model.

| Metric    | Value             |
| --------- | ----------------- |
| AUC       | **0.772 ± 0.055** |
| F1 Score  | 0.310             |
| Precision | 0.226             |
| Recall    | 0.499             |
| Accuracy  | 0.826             |

Subgroup performance:

* Undergraduate: **AUC = 0.796**
* Graduate: **AUC = 0.564**

---

## Key Predictors of Default Risk

Top features (aggregated importance, NEC run):

* Payment plan → **18.6%**
* Program → **16.1%**
* Campus → **12.0%**
* GPA → **11.9%**
* Credits earned → **9.4%**
* Current balance → **7.7%**

Default risk is driven by a combination of:
**financial behavior + academic performance + institutional context**

---

## Segmentation Insights

FRIS identifies high-risk populations across 8 dimensions.

### Academic Performance

* GPA < 2.0 → **16.6% default rate**
* GPA 3.5–4.0 → **3.0%**

### Student Type

* Returning students → **33.3% (highest risk segment)**

### Graduation Impact

* Not graduated → **11.9%**
* Graduated → **4.1%**

### Program-Level Risk

Several programs exceed **20% default rate**, indicating structural risk concentrations.

---

## Policy Insight (Critical Finding)

Income-Driven Repayment (IDR) plans show:

* **0.7% default rate (IDR borrowers)**
* **9.6% default rate (non-IDR borrowers)**

This highlights a **clear policy lever for default prevention**: proactive IDR enrollment counseling for at-risk students.

---

## Impact

FRIS enables:

* Early risk detection
* Targeted financial interventions
* Improved student outcomes
* Reduced institutional default exposure

This framework transforms student financial services from **reactive operations to predictive risk management**.

---

## Data Privacy & Compliance

* No real student data included in this repository
* Session data is stored in `data/sessions/` (mounted as a Docker volume, excluded from git)
* FERPA-compliant design
* Institutional data usage restricted to authorized environments

---

## Author

**Glauber Franca Rocha**
Student Financial Services · New England College

Applied research in:

* Predictive analytics
* Financial risk modeling
* Higher education systems

---

## License

Educational and research use only.
Institutional data access restricted.
