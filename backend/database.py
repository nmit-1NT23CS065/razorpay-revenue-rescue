import os
import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "data/transactions.db"
CSV_FILE = "data/transactions.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT NOT NULL,
    status TEXT NOT NULL,
    failure_reason TEXT DEFAULT ''
)
"""

def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_FILE)

def initialize_database():
    """Create the SQLite database and import the existing CSV once."""
    with get_connection() as conn:
        conn.execute(SCHEMA)
        count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

        if count == 0 and os.path.exists(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            expected = [
                "transaction_id", "timestamp", "amount",
                "payment_method", "status", "failure_reason"
            ]
            df = df[expected].copy()

            df.to_sql(
                "transactions",
                conn,
                if_exists="append",
                index=False
            )
            conn.commit()

def get_transactions():
    initialize_database()
    with get_connection() as conn:
        df = pd.read_sql_query(
            "SELECT transaction_id, timestamp, amount, payment_method, "
            "status, failure_reason FROM transactions ORDER BY timestamp",
            conn
        )
        df = df.astype(object).where(pd.notna(df), None)
        return df

def transaction_exists(transaction_id):
    initialize_database()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM transactions WHERE transaction_id = ?",
            (transaction_id,)
        ).fetchone()
        return row is not None

def insert_transaction(
    transaction_id,
    timestamp,
    amount,
    payment_method,
    status,
    failure_reason=""
):
    initialize_database()

    if transaction_exists(transaction_id):
        raise ValueError(f"Transaction {transaction_id} already exists.")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO transactions
            (transaction_id, timestamp, amount, payment_method, status, failure_reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_id,
                timestamp,
                float(amount),
                payment_method,
                status,
                failure_reason or ""
            )
        )
        conn.commit()

    return {
        "transaction_id": transaction_id,
        "timestamp": timestamp,
        "amount": float(amount),
        "payment_method": payment_method,
        "status": status,
        "failure_reason": failure_reason or ""
    }

def generate_transaction_id():
    initialize_database()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT transaction_id
            FROM transactions
            WHERE transaction_id LIKE 'TXN%'
            ORDER BY CAST(SUBSTR(transaction_id, 4) AS INTEGER) DESC
            LIMIT 1
            """
        ).fetchone()

    if not row:
        return "TXN00001"

    try:
        number = int(row[0][3:]) + 1
        return f"TXN{number:05d}"
    except (ValueError, TypeError):
        return f"TXN{datetime.now().strftime('%H%M%S')}"

def database_summary():
    df = get_transactions()
    failed = df[df["status"].astype(str).str.lower() == "failed"]
    successful = df[df["status"].astype(str).str.lower() == "success"]

    total = len(df)
    failure_rate = (len(failed) / total * 100) if total else 0

    return {
        "total_transactions": int(total),
        "successful_transactions": int(len(successful)),
        "failed_transactions": int(len(failed)),
        "failure_rate": round(failure_rate, 2),
        "revenue_at_risk": int(failed["amount"].sum()) if len(failed) else 0
    }
