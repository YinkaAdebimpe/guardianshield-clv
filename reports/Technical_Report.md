# Customer Lifetime Value — Technical Report

**Client:** GuardianShield Insurance *(fictional)*
**Engagement:** Customer Lifetime Value Prediction
**Prepared by:** Yinka Adebimpe, Data Scientist | Customer Analytics & Predictive Modelling
**Date:** October 2026

---

## 1. Introduction & Scope

### 1.1 Objective

GuardianShield Insurance required a customer-level model of 12-month forward Customer Lifetime Value (CLV). The model needed to:

1. Produce a pound-denominated revenue forecast per customer
2. Account for each customer's probability of remaining active
3. Support segment-level retention decisions
4. Be fully reproducible from source data to final output

### 1.2 Scope

The engagement covers a book of **5,000 policyholders** across five product lines (Motor, Home, Life, Travel, Pet). CLV is modelled at the **customer level**, not by product, because policy type does not vary premium in the synthetic dataset — a limitation documented in Section 6.

### 1.3 Deliverables

| Deliverable | Location |
|-------------|----------|
| RFM segmentation notebook | `notebooks/01_rfm_analysis.ipynb` |
| BG/NBD evaluation (negative result) | `notebooks/02a_clv_bgnbd_baseline.ipynb` |
| Survival analysis CLV notebook | `notebooks/02b_clv_survival.ipynb` |
| This report | `reports/Technical_Report.md` |
| Executive Summary | `reports/Executive_Summary.md` |
| Predictions table | PostgreSQL `clv.clv_predictions`, `data/processed/clv_predictions_v2.csv` |

---

## 2. Data

### 2.1 Source

The engagement uses **fully synthetic transaction data** generated from a reproducible Python pipeline (`src/generate_synthetic_insurance_data.py`). Real client data was not available; synthetic data was used to demonstrate methodology on realistic insurance behaviour.

**Rationale:** synthetic data allows full control over segment structure, enabling clean validation of the modelling approach without privacy or commercial constraints.

### 2.2 Scale and dimensions

| Property | Value |
|----------|-------|
| Customers | 5,000 |
| Transactions | 107,884 |
| Observation window | June 2020 – December 2025 (5.5 years) |
| Snapshot date | 2025-12-29 |
| Payment cadences | Monthly (75%) and Annual (25%) |
| Policy types | Motor, Home, Life, Travel, Pet |

### 2.3 Segment design

Three latent segments were designed with distinct premium, renewal, and churn behaviour:

| Segment | Share | Annual premium (mean) | Renewal probability | Max tenure |
|---------|-------|----------------------|---------------------|------------|
| Loyal | 25% | £900 | 0.97 | 8 years |
| Standard | 50% | £650 | 0.88 | 5 years |
| Price-sensitive | 25% | £420 | 0.65 | 3 years |

**Design intent:** segments differentiate on three dimensions simultaneously — premium level, renewal propensity, and maximum tenure. This ensures downstream models (RFM, survival analysis) can validate segment structure on independent signals.

### 2.4 Data quality checks

| Check | Result |
|-------|--------|
| All customers have ≥1 transaction | ✅ |
| `recency <= T` for all lifetimes inputs | ✅ |
| Date ranges valid (start ≤ end) | ✅ |
| Renewal events correctly flagged | ✅ |
| Segment proportions match design | ✅ (25/50/25) |

### 2.5 Known data characteristics

- **Churn rate:** 32.9% overall — within realistic UK insurance retention benchmarks
- **Payment cadence bias:** transaction counts differ 12× between monthly and annual payers for identical customer value. This is addressed by using **renewal count**, not transaction count, as the frequency signal.
- **Right-skewed monetary distribution:** premium follows a log-normal distribution; monetary value per customer is heavily concentrated at the lower end.

---

## 3. Methodology

### 3.1 RFM analysis

**Purpose:** Establish baseline behavioural segments and validate that the designed latent segments are recoverable from transactional signals alone.

**Definitions:**

| Dimension | Definition | Rationale |
|-----------|-----------|-----------|
| Recency | Days since last transaction | Continuous, no cadence bias |
| Frequency | **Renewal count** | Removes payment-cadence bias (monthly vs annual) |
| Monetary | Total premium paid | Sum across all payments |

**Scoring:** Each dimension split into quintiles (1–5), with recency inverted so lower days = higher score. Combined RFM string (e.g. `"555"` = best on all dimensions).

**Validation:** RFM scores compared against ground-truth segment labels to confirm the framework independently rediscovers the designed structure.

### 3.2 BG/NBD evaluation and rejection

**Why BG/NBD was considered:** BG/NBD is the industry-standard probabilistic model for CLV in e-commerce and retail, estimating per-customer transaction rate and dropout probability from observed frequency, recency, and tenure.

**Why it was rejected:**

BG/NBD assumes continuous-time purchase behaviour — customers transact at any time, and churn is inferred from gaps between transactions. Insurance renewals are **contractual and annual**: one renewal decision per policy year, at a fixed anniversary date.

Fitting BG/NBD produced **degenerate parameters** across three penalizer settings:

| Penalizer | r | alpha | a | b | Interpretation |
|-----------|---|---|---|---|----------------|
| 0.001 | 7.12 | 3403.53 | ≈ 0 | ≈ 0 | No dropout signal |
| 0.1 | 1.27 | 595.61 | ≈ 0 | ≈ 0 | No dropout signal |
| 0.5 | 0.66 | 302.92 | ≈ 0 | ≈ 0 | No dropout signal |

When `a ≈ 0` and `b ≈ 0`, the model detects **no churn** — every customer is treated as permanently active. This is mathematically correct for data where renewals happen on schedule for everyone, but practically useless for CLV.

**Decision:** Rather than force BG/NBD (e.g. by substituting payment events for renewals, which would reintroduce cadence bias), we switched to survival analysis — the correct framework for contractual data. The BG/NBD notebook is retained in the repository as a **documented negative result** to demonstrate model selection judgement.

### 3.3 Survival analysis

**Purpose:** Model time-to-churn directly, producing both segment-level survival curves and customer-level retention probabilities.

**Approach:**

1. **Kaplan-Meier estimation** — non-parametric survival curves, computed overall and per segment
2. **Log-rank test** — statistical comparison of survival distributions between segments
3. **Cox Proportional Hazards** — semi-parametric regression identifying feature-level churn risk

**Cox PH specification:**

| Feature | Type | Notes |
|---------|------|-------|
| `annual_premium` | continuous | Normalised annual premium per customer |
| `customer_age` | continuous | Years |
| `excess_amount` | continuous | Voluntary excess |
| `no_claims_discount` | continuous | 0.0–0.7 |
| `segment_standard` | dummy | Reference: loyal |
| `segment_price_sensitive` | dummy | Reference: loyal |
| `policy_type_*` | dummies | Reference: Motor |
| `payment_frequency_Monthly` | dummy | Reference: Annual |
| `acquisition_channel_*` | dummies | Reference: Broker |

**Penalizer:** 0.01 (L2 regularisation to reduce overfitting)

**Duration:** months from policy start to churn, or to snapshot (censored)

**Event:** 1 if churned, 0 if still active

### 3.4 CLV computation

12-month CLV per customer:

```text
CLV = annual premium × 12-month survival probability × present-value factor
```

**Present-value factor:**

```text
PV factor = (1/12) × Σ(t=1..12) [ 1 / (1 + r)^t ]
```

with **r = 0.01 monthly** (≈ 12.7% annual).

**Computed value:** **0.9379** — the average discount across the 12-month horizon.

**Survival floor:** customers whose tenure exceeded the observed range of their segment's KM curve were assigned a floor survival probability of **0.10** rather than 0, to avoid zero-CLV artefacts.

---

## 4. Results

### 4.1 RFM analysis

**Segment rediscovery — all three RFM dimensions separate cleanly:**

| Segment | Avg R score | Avg F (renewal) score | Avg M score |
|---------|-------------|----------------------|-------------|
| Loyal | 3.53 | 3.44 | 3.79 |
| Standard | 3.14 | 3.12 | 3.14 |
| Price-sensitive | 2.25 | 2.32 | 1.92 |

**Gaps between loyal and price-sensitive:**
- Recency: **1.28 points** (v1 baseline: 0.36)
- Renewal frequency: **1.12 points** (v1: 0.32)
- Monetary: **1.87 points**

**Interpretation:** RFM independently rediscovered the designed segment structure across all three dimensions. This validates both the data generation logic and the RFM methodology.

**Cadence bias observation:** Raw transaction frequency produced visibly lumpy distributions driven by monthly vs annual payment structure. Renewal-based frequency produced a smooth, bounded distribution. The choice of renewal count as the frequency signal is therefore empirically justified.

### 4.2 Survival curves

**Median survival time:**

| Segment | Median survival |
|---------|-----------------|
| Loyal | ∞ (never reaches 50% churn within window) |
| Standard | 72.0 months |
| Price-sensitive | 24.0 months |

**Log-rank test (loyal vs price-sensitive):**
- Test statistic: **1175.43**
- p-value: **< 0.000001**

**Interpretation:** the survival distributions of loyal and price-sensitive customers differ by an order of magnitude more than typical significance thresholds. Segment membership is a strong determinant of retention.

### 4.3 Cox Proportional Hazards

**Model performance:**
- Concordance index: **0.770**
- Partial log-likelihood: −11,673.49
- Likelihood ratio test: 1352.88 on 13 df (p < 0.0001)

**Significant coefficients:**

| Feature | Hazard ratio | p-value | Interpretation |
|---------|--------------|---------|----------------|
| `segment_price_sensitive` | **16.12** | < 0.0005 | 16× churn risk vs loyal |
| `segment_standard` | **2.86** | < 0.0005 | 2.9× churn risk vs loyal |
| `payment_frequency_Monthly` | **1.18** | 0.006 | 18% higher hazard for monthly payers |
| `annual_premium` | 1.000 | < 0.0005 | Negligible per-£ effect |

**Non-significant coefficients (p > 0.05):** `customer_age`, `excess_amount`, `no_claims_discount`, all policy type dummies, all acquisition channel dummies.

**Interpretation:**
- Segment membership dominates churn risk by an order of magnitude
- Monthly payment frequency independently increases churn risk by 18% — consistent with real UK insurance observations that monthly payers are more likely to lapse
- Product line, acquisition channel, and customer demographics do **not** predict churn once segment is known

### 4.4 CLV predictions

**12-month CLV by segment:**

| Segment | Customers | Avg premium | 12m survival | Avg CLV | Total CLV |
|---------|-----------|-------------|--------------|---------|-----------|
| Loyal | 1,259 | £1,101.83 | 97.0% | **£1,006.41** | £1,267,066 |
| Standard | 2,500 | £825.13 | 86.0% | £672.82 | **£1,682,049** |
| Price-sensitive | 1,241 | £554.75 | 58.0% | £308.16 | £382,425 |
| **Total** | **5,000** | — | — | — | **£3,331,540** |

**Distribution of CLV:**
- Mean: £666.31
- Median: £600.22
- Max: £4,277.20
- Min: £13.36

**Top 5 customers by CLV:**

| Customer | Segment | Annual premium | Survival | CLV |
|----------|---------|----------------|----------|-----|
| GS-003865 | **standard** | £4,947.05 | 0.92 | £4,277.20 |
| GS-003444 | **standard** | £4,612.85 | 0.92 | £3,988.26 |
| GS-004077 | loyal | £4,104.98 | 0.96 | £3,679.60 |
| GS-002609 | loyal | £3,707.29 | 0.99 | £3,432.91 |
| GS-004279 | loyal | £3,549.12 | 0.99 | £3,286.45 |

**Key observation:** the two highest-CLV customers are standard-segment with unusually high premiums, not loyal. Retention targeting based purely on segment label would miss them. Customer-level CLV is more informative than segment-level averages.

---

## 5. Validation & Sensitivity

### 5.1 Segment separation

The designed 25/50/25 split was preserved across all three downstream models:
- RFM: distinct average scores across all three dimensions
- Survival: median survival times of ∞ / 72 / 24 months
- CLV: average CLV of £1,006 / £673 / £308

### 5.2 Model performance benchmarks

| Model | Metric | Value | Benchmark |
|-------|--------|-------|-----------|
| Cox PH | Concordance | 0.770 | > 0.70 = useful |
| Log-rank | Test statistic | 1175.43 | > 50 = strong |
| Cox PH | LR test p-value | < 0.0001 | Significant |

### 5.3 Data version iteration

An earlier data version (v1) produced weak segment separation on frequency dimensions (gaps of 0.14 and 0.32 points on F and R scores). Diagnosis: segments differed only in premium and churn probability, not in renewal behaviour. The generator was rebuilt (v2) to differentiate renewal propensity and maximum tenure across segments. RFM gaps widened by 3–4× as a result. This iteration is documented in the repository.

---

## 6. Limitations

**1. Synthetic data** — reproduces realistic insurance behaviour but is not real client data. Segment parameters were tuned to reflect UK insurance retention benchmarks, but real-world distributions may differ.

**2. Customer-level CLV only** — policy type does not vary premium in the synthetic dataset. CLV is modelled per customer, not per product line. Product-level CLV would require a premium distribution correlated with policy type.

**3. 12-month horizon** — predictions beyond 12 months require additional survival assumptions. A 24–36 month horizon is a natural extension.

**4. Fixed discount rate** — 1% monthly (≈ 12.7% annual) is a modelling assumption. Real cost of capital may differ by product or customer segment.

**5. Censoring** — customers who joined recently have shorter observation windows and wider CLV uncertainty. The KM-based approach handles this correctly but confidence intervals widen near the horizon edge.

**6. Proportional hazards assumption** — Cox PH assumes hazard ratios are constant over time. This was not formally tested (e.g. Schoenfeld residuals); a stratified or time-varying model may be more appropriate if the assumption is violated.

**7. Binary churn** — the model treats churn as a single event. In practice, customers may downgrade rather than fully lapse, which the current model does not capture.

---

## 7. Reproducibility

The full pipeline runs end-to-end from a clean clone:

```bash
# Clone
git clone https://github.com/YinkaAdebimpe/guardianshield-clv.git
cd guardianshield-clv

# Environment
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Configure database
cp .env.example .env
# Edit .env with Postgres credentials

# Generate and load data
cd src
python generate_synthetic_insurance_data.py
python load_to_postgres.py
cd ..

# Run notebooks
jupyter lab
# Execute notebooks in order:
#   01_rfm_analysis.ipynb
#   02a_clv_bgnbd_baseline.ipynb  (optional)
#   02b_clv_survival.ipynb        (primary)
```

**Environment requirements:**
- Python 3.12+
- PostgreSQL 14+
- Database `guardianshield_db` (schema `clv` created automatically)

**Reproducibility controls:**
- All random seeds fixed (`RANDOM_SEED = 42`)
- Snapshot date fixed at 2025-12-29
- Data generation is deterministic
- Notebooks are self-contained (no hidden state dependencies)

---

## 8. Appendix

### 8.1 SQL reference queries

**Segment profile:**

```sql
SELECT
    c.segment,
    COUNT(DISTINCT c.customer_id) AS customers,
    ROUND(AVG(c.churned::int)::numeric * 100, 1) AS churn_pct,
    COUNT(t.transaction_id) AS transactions,
    ROUND(AVG(t.premium_amount)::numeric, 2) AS avg_premium
FROM clv.customers c
JOIN clv.transactions t USING (customer_id)
GROUP BY c.segment
ORDER BY c.segment;
```

**CLV summary:**

```sql
SELECT
    segment,
    COUNT(*) AS customers,
    ROUND(AVG(annual_premium)::numeric, 2) AS avg_premium,
    ROUND(AVG(survival_12m)::numeric, 3) AS avg_survival,
    ROUND(AVG(clv_12m)::numeric, 2) AS avg_clv,
    ROUND(SUM(clv_12m)::numeric, 2) AS total_clv
FROM clv.clv_predictions
GROUP BY segment
ORDER BY avg_clv DESC;
```

### 8.2 Notebook outputs

Key outputs referenced in this report:

| Output | Notebook | Cell |
|--------|----------|------|
| RFM validation table | `01_rfm_analysis.ipynb` | Cell 9 |
| KM curves | `02b_clv_survival.ipynb` | Cell 5 |
| Log-rank test | `02b_clv_survival.ipynb` | Cell 6 |
| Cox PH coefficients | `02b_clv_survival.ipynb` | Cell 7 |
| CLV by segment | `02b_clv_survival.ipynb` | Cell 10 |

### 8.3 Visualisations

| File | Content |
|------|---------|
| `images/rfm_distributions.png` | RFM histograms showing cadence bias |
| `images/rfm_heatmaps.png` | Segment RFM heatmap + top combinations |
| `images/rfm_segment_comparison.png` | Monetary and renewal boxplots by segment |
| `images/survival_curves.png` | Kaplan-Meier curves by segment |
| `images/clv_analysis.png` | CLV distribution, survival vs CLV, CLV by segment |

---

*Prepared as part of the OkYeahInsight Analytics portfolio — a three-engagement consulting series for GuardianShield Insurance.*