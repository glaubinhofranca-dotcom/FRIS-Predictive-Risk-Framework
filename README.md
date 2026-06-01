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

## Dataset Overview

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

---

### Feature Engineering

**Academic & Enrollment**

* GPA
* Credits earned
* Graduation status
* Withdrawal indicators
* Academic level (LEVL_CODE — Banner authoritative field)
* Program and student type

**Financial & Loan Data**

* Number of loans
* Original loan amount
* Current balance
* Payment plan

---

### Modeling Approach

* 5-fold Stratified Cross-Validation
* Class imbalance handled with `class_weight="balanced"`
* Models evaluated:

  * Logistic Regression
  * Random Forest
  * Gradient Boosting

---

## Model Performance

**Best Model: Random Forest**

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

Top features (aggregated importance):

* Payment plan → **18.6%**
* Program → **16.1%**
* Campus → **12.0%**
* GPA → **11.9%**
* Credits earned → **9.4%**
* Current balance → **7.7%**

👉 Default risk is driven by a combination of:
**financial behavior + academic performance + institutional context**

---

## Segmentation Insights

FRIS identifies high-risk populations:

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

👉 This highlights a **clear policy lever for default prevention**

---

## Impact

FRIS enables:

* Early risk detection
* Targeted financial interventions
* Improved student outcomes
* Reduced institutional default exposure

This framework transforms student financial services from **reactive operations to predictive risk management**.

---

## System Architecture

```
ETL → Feature Engineering → ML Modeling → Evaluation → Segmentation
```

**Core Components:**

* `fris_etl.py`
* `fris_model.py`
* `fris_segmentation.py`

---

## Reproducibility

* Modular pipeline
* Fully reproducible outputs
* Clean separation of data and code
* Independent generation of analytical visuals

---

## Data Privacy & Compliance

* No real student data included
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