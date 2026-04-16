# FRIS — Financial Risk Identification System

**New England College · Student Financial Services**

FRIS is a machine learning system that predicts the likelihood of student federal loan default using academic, enrollment, and financial aid data from Banner/Ellucian. It enables Student Financial Services staff to identify at-risk students early and intervene before a loan crosses the 270-day federal delinquency threshold.

---

## Background

Federal student loan default carries serious consequences for both students (credit damage, wage garnishment, loss of future aid eligibility) and institutions (cohort default rate penalties, potential loss of Title IV funding). Traditional approaches to identifying at-risk borrowers are reactive — students are contacted only after they have already missed payments for months.

FRIS shifts the model to **proactive identification**, flagging risk patterns at the time of enrollment or early in the academic year, when intervention is still possible.

---

## Project Structure

```
FRIS/
├── .gitignore
├── fris_best_model.pkl       # Trained model artifact (not tracked)
├── fris_etl.py               # ETL pipeline: raw Banner exports → dataset_fris.csv
├── fris_model.py             # ML model: cross-validation, feature importance, model export
├── fris_segmentation.py      # Segmentation analysis across all key dimensions
├── dataset_fris.csv          # Processed dataset (not tracked — contains PII)
├── README.md
└── requirements.txt
```

---

## Data Sources

All data is sourced from Banner/Ellucian exports provided by NEC Information Technology:

| File | Contents |
|------|----------|
| `Borrower Details.xlsx` | Loan servicer data joined with Banner academic/enrollment records |

**Population:** 1,302 active students (UG: 992 · UA: 133 · GR: 211 · excluding @00 undeposited prospects)

---

## Methodology

### Target Variable
A student is flagged as **default** if `Days Delinquent > 270`, consistent with the U.S. Department of Education's federal definition of loan default.

### Features

| Feature | Source | Type |
|---------|--------|------|
| GPA | Banner SHRTGPA | Numeric |
| Credits earned | Banner academic record | Numeric |
| Graduated status | Banner GRADUATED_IND | Binary |
| Withdrawn status | Banner SFBETRM_ESTS_CODE | Binary |
| Level (UG/GR) | Banner LEVL_CODE | Categorical |
| Program | Banner PROGRAM | Categorical |
| Student type | Banner STYP_DESC | Categorical |
| Campus code | Banner CAMP_CODE | Categorical |
| Number of loans | Servicer data | Numeric |
| Original loan amount | Servicer data | Numeric |
| Current balance | Servicer data | Numeric |
| Payment plan status | Servicer data | Binary |

**Withdrawn codes:** `WD`, `W4`, `W6`, `W7` (weeks 4, 6, 7)

### Model Pipeline

- Preprocessing: median imputation for numeric features, constant imputation + one-hot encoding for categorical
- Class imbalance: `class_weight="balanced"` on all classifiers (default rate: 7.5%)
- Evaluation: 5-fold stratified cross-validation
- Models tested: Logistic Regression, Random Forest, Gradient Boosting

---

## Results

**Best model: Random Forest · AUC 0.740 ± 0.032**

| Model | AUC | F1 | Precision | Recall |
|-------|-----|-----|-----------|--------|
| Logistic Regression | 0.719 ± 0.056 | 0.248 | 0.160 | 0.558 |
| Random Forest | **0.740 ± 0.032** | **0.279** | **0.210** | **0.427** |
| Gradient Boosting | 0.726 ± 0.047 | 0.097 | 0.233 | 0.062 |

### Top Features by Importance

| Rank | Feature | Importance |
|------|---------|-----------|
| 1 | GPA | 17.6% |
| 2 | Credits earned | 10.9% |
| 3 | Current balance | 9.0% |
| 4 | Original loan amount | 7.7% |
| 5 | Graduated | 6.9% |
| 6 | Number of loans | 5.9% |

### Key Segmentation Findings

| Segment | Default Rate | vs. Overall |
|---------|-------------|-------------|
| GPA < 2.0 | 16.6% | +9.1 pp |
| Not graduated | 11.9% | +4.4 pp |
| Returning Student type | 33.3% | +25.8 pp |
| Campus XU | 23.6% | +16.1 pp |
| BSN Nursing | 0.0% | −7.5 pp |
| Graduated | 4.1% | −3.4 pp |

---

## Setup

```bash
# Clone repository
git clone https://github.com/glaubinhofranca-dotcom/FRIS-Predictive-Risk-Framework.git
cd fris

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Pipeline

```bash
# Step 1: build dataset from Borrower Details.xlsx
python fris_etl.py

# Step 2: train and evaluate models
python fris_model.py

# Step 3: run segmentation analysis
python fris_segmentation.py
```

---

## Privacy & Compliance

- All data files containing student PII are excluded via `.gitignore`
- Dataset is used exclusively for institutional financial aid risk management
- Access restricted to authorized Student Financial Services staff
- FERPA compliance maintained — no individual student predictions are shared externally

---

## Roadmap

- [ ] Add historical cohorts (2018–2022) to increase training data and model robustness
- [ ] Build a Streamlit dashboard for SFS staff (no-code risk score lookup)
- [ ] Automate weekly ETL refresh from Banner
- [ ] Add early alert integration with NEC advising system

---

## Author

**Glauber Franca-Rocha**
Student Financial Services · New England College
FRIS is part of ongoing research in institutional financial risk modeling for higher education.
