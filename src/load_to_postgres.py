# ============================================
# GUARDIANSHIELD INSURANCE
# ENGAGEMENT 2 — LOAD SYNTHETIC DATA TO POSTGRES
# ============================================

import pandas as pd
from sqlalchemy import create_engine, text

from config import DB_URL, DB_SCHEMA, RAW_DATA_DIR


def load_csvs():
    """Read the generated CSVs into pandas DataFrames."""
    customers = pd.read_csv(RAW_DATA_DIR / "customers.csv")
    transactions = pd.read_csv(RAW_DATA_DIR / "transactions.csv")

    # Parse dates so Postgres stores them as DATE, not TEXT
    customers["policy_start_date"] = pd.to_datetime(customers["policy_start_date"]).dt.date
    customers["churned_date"] = pd.to_datetime(customers["churned_date"], errors="coerce").dt.date
    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"]).dt.date

    return customers, transactions


def ensure_schema(engine):
    """Create the clv schema if it doesn't exist."""
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA};"))
        print(f"Schema '{DB_SCHEMA}' ready.")


def write_table(df: pd.DataFrame, table_name: str, engine):
    """Write a DataFrame to Postgres, replacing the table if it exists."""
    df.to_sql(
        name=table_name,
        con=engine,
        schema=DB_SCHEMA,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )
    print(f"Wrote {len(df):,} rows → {DB_SCHEMA}.{table_name}")


if __name__ == "__main__":
    print("Reading CSVs...")
    customers, transactions = load_csvs()

    print(f"Loaded customers: {len(customers):,}")
    print(f"Loaded transactions: {len(transactions):,}")

    print("\nConnecting to Postgres...")
    engine = create_engine(DB_URL)

    ensure_schema(engine)

    print("\nWriting tables...")
    write_table(customers, "customers", engine)
    write_table(transactions, "transactions", engine)

    # Quick verification query
    with engine.connect() as conn:
        cust_count = conn.execute(
            text(f"SELECT COUNT(*) FROM {DB_SCHEMA}.customers;")
        ).scalar()
        tx_count = conn.execute(
            text(f"SELECT COUNT(*) FROM {DB_SCHEMA}.transactions;")
        ).scalar()

    print(f"\nVerification:")
    print(f"  {DB_SCHEMA}.customers:    {cust_count:,} rows")
    print(f"  {DB_SCHEMA}.transactions: {tx_count:,} rows")

    print("\n✓ Data loaded successfully.")