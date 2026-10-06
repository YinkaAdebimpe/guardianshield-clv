# Customer Lifetime Value — Executive Summary

**Client:** GuardianShield Insurance *(fictional)*
**Engagement:** Customer Lifetime Value Prediction
**Prepared by:** Yinka Adebimpe, Data Scientist | Customer Analytics & Predictive Modelling
**Date:** October 2026

---

## 1. Overview

GuardianShield Insurance engaged us to answer a single question: **which customers are most valuable, and where should retention budget be spent?**

The result is a 12-month Customer Lifetime Value (CLV) model covering all **5,000 policyholders** in the book. Each customer receives a predicted pound-value over the next year, adjusted for their probability of remaining active.

This is not a segmentation exercise. It is a revenue forecast at the individual customer level, designed to inform retention prioritisation.

---

## 2. Key Findings

**1. Total projected 12-month CLV: £3.33M**
This represents expected retained revenue across the current book, assuming no new customers are acquired.

**2. Loyal customers are worth 3.3× more per customer than price-sensitive**
Average 12-month CLV by segment:
- Loyal: **£1,006**
- Standard: £673
- Price-sensitive: £308

**3. Standard customers drive the largest total portfolio value: £1.68M**
Despite being worth less per customer than loyal, the standard segment is twice as large and contributes the highest total revenue. This is the highest-volume growth opportunity.

**4. Retention varies dramatically by segment**
12-month survival probability:
- Loyal: **97%**
- Standard: 86%
- Price-sensitive: 58%

**5. Segment membership is the dominant churn driver**
A Cox Proportional Hazards model (concordance 0.77) shows price-sensitive customers are **16.1× more likely to churn** than loyal, holding all other factors constant. Payment frequency contributes an additional 18% hazard for monthly payers.

---

## 3. Segment Profile

| Segment | Customers | Avg premium | 12m survival | Avg CLV | Total CLV |
|---------|-----------|-------------|--------------|---------|-----------|
| Loyal | 1,259 | £1,102 | 97% | **£1,006** | £1.27M |
| Standard | 2,500 | £825 | 86% | £673 | **£1.68M** |
| Price-sensitive | 1,241 | £555 | 58% | £308 | £0.38M |

---

## 4. Recommendations

### Priority 1 — Protect the loyal segment

**Action:** Loyalty rewards, early renewal incentives, dedicated account management for top-decile CLV customers.

**Impact:** Loyal customers contribute £1.27M in projected CLV. A 5-percentage-point retention improvement in this segment is worth approximately **£65,000** in incremental annual revenue.

### Priority 2 — Grow the standard segment into loyal behaviour

**Action:** Cross-sell, upsell, and migrate monthly payers to annual contracts.

**Impact:** The standard segment is the largest (£1.68M portfolio CLV) but retains at only 86%. Closing the retention gap with loyal by 10 percentage points is worth roughly **£170,000** in additional annual CLV.

### Priority 3 — Accept churn in the price-sensitive segment

**Action:** Maintain low-cost servicing. Do not allocate retention budget to this segment.

**Impact:** £308 average CLV does not justify retention spend. The segment contributes £0.38M in total CLV but at high servicing cost per retained pound.

**Note on high-value outliers:** The two highest-CLV customers in the book are classified as standard, not loyal — each worth over £4,000 in 12-month CLV. Customer-level targeting should identify high-premium customers regardless of segment label.

---

## 5. Method Summary

Three modelling approaches were evaluated:

1. **RFM segmentation** — established baseline behavioural segments (Recency, Frequency, Monetary)
2. **BG/NBD probabilistic model** — evaluated and rejected. The model collapsed to degenerate parameters because insurance renewals are contractual and annual, not continuous-time purchases. This negative result is documented in the repository.
3. **Survival analysis** — selected as the primary framework. Kaplan-Meier curves established segment-level survival, and a Cox Proportional Hazards model quantified feature-level churn risk.

12-month CLV was computed as:

```text
CLV = annual premium × survival probability × present-value factor
```

with a 1% monthly discount rate.

---

## 6. Scope & Limitations

**Synthetic data** — This engagement uses fully reproducible synthetic data rather than real client data. Segment parameters were tuned to reflect UK insurance retention benchmarks.

**Customer-level CLV** — Policy type (Motor, Home, Life, Travel, Pet) is captured as a customer attribute but does not vary premium in the current dataset. CLV is therefore modelled per customer rather than per product line. Extending to product-level CLV would require a premium distribution correlated with policy type.

**12-month horizon** — Predictions beyond 12 months would require additional survival assumptions. A 24–36 month horizon is a natural next iteration.

---

## 7. Appendix

**Data**
- 5,000 customers, 107,884 transactions, 5.5-year window (June 2020 – December 2025)
- Snapshot date: 2025-12-29

**Model performance**
- Cox Proportional Hazards concordance: **0.770**
- Log-rank test (loyal vs price-sensitive): statistic 1175.43, p < 0.000001

**Repository**
- Full code, notebooks, and documentation: [github.com/YinkaAdebimpe/guardianshield-clv](https://github.com/YinkaAdebimpe/guardianshield-clv)
- Notebooks: RFM analysis, BG/NBD baseline (negative result), survival analysis CLV model
- Data pipeline: synthetic generator + PostgreSQL loader

---

*Prepared as part of the OkYeahInsight Analytics portfolio — a three-engagement consulting series for GuardianShield Insurance.*