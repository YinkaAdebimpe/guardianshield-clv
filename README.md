# Engagement 2 — Customer Lifetime Value Prediction

**Client:** GuardianShield Insurance (fictional)
**Engagement:** Customer Lifetime Value Prediction
**Author:** Yinka Adebimpe
**Repo:** [guardianshield-clv](https://github.com/YinkaAdebimpe/guardianshield-clv)

---

## Executive Summary

GuardianShield Insurance has a book of **5,000 policyholders** across Motor, Home, Life, Travel, and Pet products. Leadership wanted to know: **which customers are most valuable, and where should retention budget be spent?**

This engagement answers that question with a **12-month Customer Lifetime Value (CLV) model** built on survival analysis. The model estimates each customer's expected revenue over the next year, factoring in their probability of remaining active.

**Headline findings:**

| Segment | Customers | Avg 12-month CLV | Portfolio CLV | 12m Survival |
|---------|-----------|------------------|---------------|--------------|
| Loyal | 1,259 | **£1,006** | £1.27M | 97% |
| Standard | 2,500 | £673 | **£1.68M** | 86% |
| Price-sensitive | 1,241 | £308 | £0.38M | 58% |

- **Total projected 12-month CLV: £3.33M**
- **Loyal customers are worth 3.3× more per customer** than price-sensitive
- **Standard customers drive the largest total portfolio value** because the segment is 2× larger
- A Cox Proportional Hazards model achieved **concordance 0.77**, confirming segment membership as the dominant churn driver (price-sensitive hazard ratio: **16.1**)

**Recommended actions:**

1. **Protect** the loyal segment with loyalty rewards and early renewal incentives
2. **Grow** the standard segment into loyal behaviour — highest volume opportunity
3. **Accept** churn in price-sensitive — retention ROI is negative

---

## Method

### Data

- **Source:** Synthetic insurance transaction data (fully reproducible via `src/generate_synthetic_insurance_data.py`)
- **Scale:** 5,000 customers, 107,884 transactions, 5.5-year window (2020-06 to 2025-12)
- **Segments:** Three latent segments with distinct premium, churn, and renewal behaviour

### Approach

1. **RFM analysis** (`notebooks/01_rfm_analysis.ipynb`) — Recency, Frequency, Monetary segmentation with dual frequency definitions (transaction-count vs renewal-count) to remove payment-cadence bias
2. **BG/NBD baseline** (`notebooks/02a_clv_bgnbd_baseline.ipynb`) — evaluated and **rejected** (see Negative Result below)
3. **Survival analysis** (`notebooks/02b_clv_survival.ipynb`) — Kaplan-Meier + Cox Proportional Hazards + 12-month CLV

### Why survival analysis instead of BG/NBD

BG/NBD assumes continuous-time purchase behaviour (e-commerce). Insurance renewals are **contractual and annual** — one renewal decision per policy year at a fixed anniversary. BG/NBD collapsed to degenerate parameters (`a ≈ 0`, `b ≈ 0`) across three penalizer settings.

Rather than force a model that didn't fit, we switched to survival analysis — the correct framework for subscription/contractual data. The BG/NBD notebook is retained as a **documented negative result** (see `notebooks/02a_clv_bgnbd_baseline.ipynb`).

---

## Repository structure

```text
.
├── data/
│   ├── raw/                          # Generated CSVs (gitignored)
│   └── processed/                    # Committed summary CSVs for GitHub review
│       ├── rfm_v2.csv
│       └── clv_predictions_v2.csv
├── images/                           # Analysis plots
├── notebooks/
│   ├── 01_rfm_analysis.ipynb         # RFM segmentation
│   ├── 02a_clv_bgnbd_baseline.ipynb  # BG/NBD (negative result)
│   └── 02b_clv_survival.ipynb        # Survival analysis CLV (primary)
├── reports/                          # Executive summary, technical report
├── sql/                              # SQL scripts
├── src/
│   ├── config.py                     # Paths, DB config, constants
│   ├── generate_synthetic_insurance_data.py
│   └── load_to_postgres.py
├── .env.example                      # Template — copy to .env and fill in
├── .gitignore
├── README.md
└── requirements.txt
```

---

## How to reproduce

### Prerequisites

- Python 3.12+
- PostgreSQL 14+ (running on `localhost:5432`)
- A database named `guardianshield_db`

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/YinkaAdebimpe/guardianshield-clv.git
cd guardianshield-clv

# 2. Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure database credentials
cp .env.example .env
# Edit .env with your Postgres password
```

### Run the pipeline

```bash
# Generate synthetic data (~5,000 customers, ~108,000 transactions)
cd src
python generate_synthetic_insurance_data.py

# Load into PostgreSQL (creates schema `clv`)
python load_to_postgres.py

# Launch Jupyter and run the notebooks in order
cd ..
jupyter lab
```

Then open the notebooks in `notebooks/` and run them in order:

1. `01_rfm_analysis.ipynb`
2. `02a_clv_bgnbd_baseline.ipynb` (optional — documents the negative result)
3. `02b_clv_survival.ipynb` (primary CLV model)

---

## Results

### Segment profile

| Segment | Customers | Churn | Median tenure | Median premium | 12-month CLV |
|---------|-----------|-------|---------------|----------------|--------------|
| Loyal | 1,259 | 7% | 32 months | £997 | £1,006 |
| Standard | 2,500 | 28% | 25 months | £740 | £673 |
| Price-sensitive | 1,241 | 70% | 12 months | £492 | £308 |

### Statistical validation

- **Log-rank test (loyal vs price-sensitive):** statistic **1175.43**, p < 0.000001
- **Cox PH concordance:** **0.770** — model correctly ranks customers by churn risk 77% of the time
- **Dominant predictors:** segment membership (HR 16.1 for price-sensitive vs loyal), payment frequency (HR 1.18 for monthly)

### Visualisations

- `images/survival_curves.png` — Kaplan-Meier survival by segment
- `images/clv_analysis.png` — CLV distribution, P(alive) vs CLV, CLV by segment
- `images/rfm_distributions.png` — RFM distributions with cadence-bias visualised
- `images/rfm_heatmaps.png` — RFM scoring heatmaps
- `images/rfm_segment_comparison.png` — Monetary and renewal boxplots

---

## Tech stack

| Layer | Tools |
|-------|-------|
| Language | Python 3.12 |
| Data manipulation | pandas, numpy |
| Statistical modelling | lifelines (Kaplan-Meier, Cox PH), lifetimes (BG/NBD — evaluated) |
| Database | PostgreSQL 18, SQLAlchemy, psycopg2 |
| Visualisation | matplotlib, seaborn |
| Notebooks | JupyterLab |
| Version control | Git, GitHub |

---

## Limitations

1. **Synthetic data** — reproduces realistic insurance behaviour but is not real client data. Segment parameters were tuned to reflect UK insurance retention benchmarks.
2. **12-month horizon** — longer horizons (24–36 months) would need additional survival assumptions.
3. **Discount rate** — fixed at 1% monthly (≈ 12.7% annual); real cost of capital may differ.
4. **Censoring** — customers who joined recently have limited observation windows; their CLV estimates carry wider uncertainty.

---

## Author

**Yinka Adebimpe**
Data Scientist | Customer Analytics & Predictive Modelling

I build end-to-end data science solutions for customer-facing businesses — from data engineering and feature design to survival analysis, machine learning, and business-ready reporting.

- GitHub: [@YinkaAdebimpe](https://github.com/YinkaAdebimpe)
- Email: adebimpey@gmail.com

---

*Part of the OkYeahInsight Analytics portfolio — a three-engagement consulting series for GuardianShield Insurance.*