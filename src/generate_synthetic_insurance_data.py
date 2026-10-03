# ============================================
# GUARDIANSHIELD INSURANCE
# ENGAGEMENT 2 — SYNTHETIC DATA GENERATION (v2)
# ============================================
# v2 changes:
#   - Segments differ in RENEWAL TENDENCY, not just premium
#   - Renewal is a per-year customer decision, not random
#   - Produces differentiated frequency signals for BG/NBD
# ============================================

from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from config import RAW_DATA_DIR, RANDOM_SEED, N_CUSTOMERS

# ============================================
# SETUP
# ============================================

np.random.seed(RANDOM_SEED)
fake = Faker("en_GB")
Faker.seed(RANDOM_SEED)

SIMULATION_START = date(2020, 1, 1)
SIMULATION_END = date(2025, 12, 31)

POLICY_TYPES = ["Motor", "Home", "Life", "Travel", "Pet"]
POLICY_TYPE_WEIGHTS = [0.40, 0.25, 0.10, 0.15, 0.10]

ACQUISITION_CHANNELS = ["Online", "Broker", "Direct", "Comparison Site"]
ACQUISITION_WEIGHTS = [0.35, 0.20, 0.15, 0.30]

# ============================================
# SEGMENTS (v2)
# ============================================
# Each segment now differs on 4 dimensions:
#   - prob:           share of customers in this segment
#   - premium_mean:   annual premium (£)
#   - renewal_prob:   probability of renewing at each anniversary
#   - base_tenure:    average years before considering churn

SEGMENTS = {
    "loyal": {
        "prob": 0.25,
        "premium_mean": 900,
        "renewal_prob": 0.98,
        "max_years": 8,
    },
    "standard": {
        "prob": 0.50,
        "premium_mean": 650,
        "renewal_prob": 0.92,
        "max_years": 6,
    },
    "price_sensitive": {
        "prob": 0.25,
        "premium_mean": 420,
        "renewal_prob": 0.75,
        "max_years": 4,
    },
}

# ============================================
# HELPERS
# ============================================

def add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, 28)
    return date(year, month, day)


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=int(np.random.randint(0, delta + 1)))


def assign_segment() -> str:
    segments = list(SEGMENTS.keys())
    probs = [SEGMENTS[s]["prob"] for s in segments]
    return np.random.choice(segments, p=probs)


# ============================================
# CUSTOMER GENERATION
# ============================================

def generate_customer(customer_index: int) -> dict:
    customer_id = f"GS-{customer_index:06d}"
    segment = assign_segment()
    seg = SEGMENTS[segment]

    earliest_start = SIMULATION_START + timedelta(days=180)
    policy_start = random_date(earliest_start, SIMULATION_END - timedelta(days=30))

    payment_frequency = np.random.choice(["Monthly", "Annual"], p=[0.75, 0.25])

    annual_premium = float(
        np.random.lognormal(mean=np.log(seg["premium_mean"]), sigma=0.35)
    )
    premium_amount = (
        round(annual_premium / 12, 2) if payment_frequency == "Monthly"
        else round(annual_premium, 2)
    )

    return {
        "customer_id": customer_id,
        "policy_id": f"POL-{customer_index:06d}-01",
        "policy_start_date": policy_start,
        "policy_type": np.random.choice(POLICY_TYPES, p=POLICY_TYPE_WEIGHTS),
        "payment_frequency": payment_frequency,
        "premium_amount": premium_amount,
        "region": fake.county(),
        "postcode": fake.postcode(),
        "customer_age": int(np.clip(np.random.normal(45, 14), 18, 80)),
        "acquisition_channel": np.random.choice(
            ACQUISITION_CHANNELS, p=ACQUISITION_WEIGHTS
        ),
        "excess_amount": float(np.random.choice([0, 100, 250, 500, 750])),
        "no_claims_discount": round(float(np.random.uniform(0, 0.7)), 2),
          "segment": segment,
        "renewal_prob": seg["renewal_prob"],
        "max_years": seg["max_years"],
    }


# ============================================
# CHURN DECISION
# ============================================

def determine_churn_date(policy_start: date, renewal_prob: float, max_years: int) -> date | None:
    """
    At each policy anniversary, the customer decides whether to renew.
    Also enforces a maximum tenure (max_years) — customers eventually lapse.
    """
    anniversary = policy_start
    years_elapsed = 0

    while anniversary <= SIMULATION_END and years_elapsed < max_years:
        if np.random.random() > renewal_prob:
            return anniversary
        anniversary = add_months(anniversary, 12)
        years_elapsed += 1

    # Reached max_years — force lapse at that anniversary
    if years_elapsed >= max_years:
        return anniversary

    return None  # still active at simulation end


# ============================================
# TRANSACTION GENERATION
# ============================================

def generate_transactions(customer: dict):
    transactions = []

    policy_start = customer["policy_start_date"]
    premium = customer["premium_amount"]
    freq = customer["payment_frequency"]
    step_months = 1 if freq == "Monthly" else 12

    churn_date = determine_churn_date(
        policy_start,
        customer["renewal_prob"],
        customer["max_years"],
    )


    # Force at least one year of payments
    if churn_date is not None and churn_date <= policy_start:
        churn_date = add_months(policy_start, 12)

    tx_date = policy_start
    tx_counter = 0
    year_first_tx_seen = set()

    while tx_date <= SIMULATION_END:
        if churn_date is not None and tx_date >= churn_date:
            break

        months_since_start = (
            (tx_date.year - policy_start.year) * 12
            + (tx_date.month - policy_start.month)
        )
        policy_year = months_since_start // 12

        # Renewal = first transaction of each policy year > 0
        renewed = policy_year >= 1 and policy_year not in year_first_tx_seen
        if renewed:
            year_first_tx_seen.add(policy_year)

        # Claims: rarer for loyal
        claims_lambda = {
            "loyal": 0.05,
            "standard": 0.10,
            "price_sensitive": 0.15,
        }[customer["segment"]]
        claims = min(int(np.random.poisson(claims_lambda)), 4)

        transactions.append({
            "customer_id": customer["customer_id"],
            "policy_id": customer["policy_id"],
            "transaction_id": f"TXN-{customer['customer_id'][3:]}-{tx_counter:04d}",
            "transaction_date": tx_date,
            "premium_amount": round(premium * np.random.uniform(0.95, 1.05), 2),
            "tenure_months": months_since_start,
            "claims_count": claims,
            "renewed": bool(renewed),
        })

        tx_counter += 1
        tx_date = add_months(tx_date, step_months)

    return transactions, churn_date


# ============================================
# BUILD DATASET
# ============================================

def build_dataset(n_customers: int = N_CUSTOMERS):
    print(f"Generating {n_customers} customers (v2)...")

    customer_records = []
    transaction_records = []

    for i in range(1, n_customers + 1):
        cust = generate_customer(i)
        txns, churn_date = generate_transactions(cust)

        if not txns:
            continue

        customer_records.append({
            "customer_id": cust["customer_id"],
            "policy_id": cust["policy_id"],
            "policy_type": cust["policy_type"],
            "payment_frequency": cust["payment_frequency"],
            "region": cust["region"],
            "postcode": cust["postcode"],
            "customer_age": cust["customer_age"],
            "acquisition_channel": cust["acquisition_channel"],
            "excess_amount": cust["excess_amount"],
            "no_claims_discount": cust["no_claims_discount"],
            "segment": cust["segment"],
            "policy_start_date": cust["policy_start_date"],
            "churned": churn_date is not None,
            "churned_date": churn_date,
        })

        transaction_records.extend(txns)

    customers_df = pd.DataFrame(customer_records)
    transactions_df = pd.DataFrame(transaction_records)

    print(f"Customers: {len(customers_df):,}")
    print(f"Transactions: {len(transactions_df):,}")
    print(f"Date range: {transactions_df['transaction_date'].min()} "
          f"to {transactions_df['transaction_date'].max()}")
    print(f"\nChurn rate: {customers_df['churned'].mean():.2%}")

    print(f"\nSegment distribution:")
    print(customers_df["segment"].value_counts(normalize=True).round(3))

    print(f"\nRenewals per segment:")
    tx_with_seg = transactions_df.merge(
        customers_df[["customer_id", "segment"]], on="customer_id"
    )
    renewals_by_seg = (
        tx_with_seg[tx_with_seg["renewed"]]
        .groupby("segment")["transaction_id"]
        .count()
        .rename("total_renewals")
    )
    customers_by_seg = customers_df.groupby("segment").size().rename("customers")
    summary = pd.concat([customers_by_seg, renewals_by_seg], axis=1)
    summary["renewals_per_customer"] = (
        summary["total_renewals"] / summary["customers"]
    ).round(2)
    print(summary)

    print(f"\nChurn rate by segment:")
    print(
        customers_df.groupby("segment")["churned"]
        .mean()
        .round(3)
    )

    return customers_df, transactions_df


if __name__ == "__main__":
    customers_df, transactions_df = build_dataset()

    customers_path = RAW_DATA_DIR / "customers.csv"
    transactions_path = RAW_DATA_DIR / "transactions.csv"

    customers_df.to_csv(customers_path, index=False)
    transactions_df.to_csv(transactions_path, index=False)

    print(f"\nSaved: {customers_path}")
    print(f"Saved: {transactions_path}")