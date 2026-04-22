# FRIS — Financial Risk Intelligence System

**Predictive Analytics for Student Loan Default Risk**
New England College · Student Financial Services

---

## Executive Summary

The **Financial Risk Intelligence System (FRIS)** is a machine learning framework designed to **predict student federal loan default risk** using academic, enrollment, and financial indicators.

Unlike traditional reactive approaches, FRIS enables **early identification of at-risk borrowers**, allowing institutions to intervene **before delinquency escalates to default (270+ days)**.

This project demonstrates how data science can be operationalized within higher education to improve **financial outcomes, compliance, and institutional risk management**.

---

## Problem Statement

Federal student loan default presents systemic challenges:

* **Students** face long-term financial harm (credit damage, wage garnishment, loss of aid eligibility)
* **Institutions** risk increased Cohort Default Rates (CDR) and potential loss of Title IV funding
* Existing processes are **reactive**, acting only after significant delinquency

---

## Solution

FRIS introduces a **proactive, data-driven framework** that:

* Identifies risk patterns **early in the student lifecycle**
* Quantifies default probability using machine learning
* Enables targeted intervention strategies for Student Financial Services teams

---

## Methodology

### Target Definition

A borrower is classified as **default** if:

```
Days Delinquent > 270
```

Aligned with the U.S. Department of Education federal definition.

---

### Feature Engineering

FRIS integrates multi-dimensional data:

**Academic & Enrollment**

* GPA
* Credits earned
* Graduation status
* Withdrawal indicators
* Academic level (Undergraduate / Graduate)
* Program and student type

**Financial & Loan Data**

* Number of loans
* Original loan amount
* Current balance
* Payment plan status

---

### Modeling Approach

* **Preprocessing**

  * Median imputation (numeric)
  * Constant imputation + One-Hot Encoding (categorical)

* **Class Imbalance Handling**

  * `class_weight="balanced"`

* **Validation Strategy**

  * 5-fold Stratified Cross-Validation

* **Models Evaluated**

  * Logistic Regression
  * Random Forest
  * Gradient Boosting

---

## Results

**Best Model: Random Forest**

| Metric    | Value             |
| --------- | ----------------- |
| AUC       | **0.740 ± 0.032** |
| F1 Score  | 0.279             |
| Precision | 0.210             |
| Recall    | 0.427             |

---

### Key Predictors

Top drivers of default risk include:

* GPA
* Credits earned
* Loan balance
* Original loan amount
* Graduation status
* Number of loans

---

### Segmentation Insights

FRIS reveals high-impact risk segments:

* Low GPA populations show significantly elevated default risk
* Non-graduated students exhibit materially higher default rates
* Specific student types and enrollment patterns concentrate risk

These insights enable **targeted, high-efficiency interventions**.

---

## Impact

FRIS supports institutions in:

* Reducing federal student loan default rates
* Improving student financial outcomes
* Protecting Title IV eligibility
* Transitioning from reactive to proactive risk management

This framework demonstrates a scalable approach to **data-driven financial risk mitigation in higher education**.

---

## System Architecture

```
ETL Pipeline → Feature Engineering → ML Modeling → Evaluation → Deployment Artifact
```

**Core Components:**

* `fris_etl.py` — Data processing and feature construction
* `fris_model.py` — Model training, validation, and export
* `fris_segmentation.py` — Risk segmentation and insights

---

## Setup

```bash
git clone https://github.com/glaubinhofranca-dotcom/FRIS-Predictive-Risk-Framework.git
cd FRIS-Predictive-Risk-Framework

python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

---

## Usage

```bash
# Build dataset
python fris_etl.py

# Train and evaluate model
python fris_model.py

# Run segmentation analysis
python fris_segmentation.py
```

---

## Data Privacy & Compliance

This repository **does not contain any real student-level data**.

* All datasets and model artifacts derived from institutional data are excluded via `.gitignore`
* Only synthetic or non-sensitive data structures are used for demonstration
* The framework is designed to operate on authorized institutional data sources

This project adheres to **FERPA guidelines**. No personally identifiable information (PII) is included or exposed.

---

## Reproducibility

The project is fully reproducible:

* Fixed dependency versions via `requirements.txt`
* Modular pipeline structure
* Clear separation between code and data

---

## Roadmap

* Expand model with multi-year historical cohorts
* Deploy interactive dashboard for institutional use
* Automate ETL pipelines
* Integrate with advising and early alert systems

---

## Author

**Glauber Franca-Rocha**
Student Financial Services · New England College

This work is part of ongoing applied research in **financial risk modeling and predictive analytics in higher education systems**.

---

## License

This project is intended for educational and research purposes.
Institutional data usage is restricted to authorized environments.