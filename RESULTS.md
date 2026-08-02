# Results

Reference results for this repository, preserved at tag `v1.0`.

Dataset: 1,302 de-identified student borrowers, aid year 2025–26, exported from a
Banner student information system.

| Metric                          | Value                        |
|---------------------------------|------------------------------|
| Borrowers analyzed              | 1,302                        |
| Defaults / baseline rate        | 98 / 7.5%                    |
| Random Forest (AUC, 5-fold CV)  | 0.772 ± 0.055                |
| Logistic Regression (AUC)       | 0.754                        |
| Gradient Boosting (AUC)         | 0.745                        |
| Subgroup AUC (UG / GR)          | 0.796 / 0.564                |
| Strongest predictor             | Payment plan (18.6%)         |
| IDR vs non-IDR default rate     | 0.7% vs 9.6%                 |

## Known limitations

The graduate-student subgroup AUC (0.564) rests on a very small number of default
cases and should not be relied upon.

One feature carries a potential data-leakage risk, documented in the pipeline notes.

Results are observational. Borrowers enrolled in income-driven repayment may differ
systematically from those who are not, in ways this dataset cannot measure.

Development after tag `v1.0` continues on separate branches; the tagged state is the
reference for the figures above.
