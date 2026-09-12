import csv
import random
from datetime import datetime, timedelta

random.seed(42)

methods = ["UPI", "Card", "NetBanking", "Wallet"]
failure_reasons = [
    "Bank timeout",
    "Insufficient funds",
    "Network error",
    "Payment declined",
    "Authentication failed",
]

rows = []

start_time = datetime(2026, 9, 1, 8, 0)

for i in range(2000):
    transaction_id = f"TXN{i+1:05d}"

    # Spread transactions across a single day
    minutes_after_start = random.randint(0, 840)
    timestamp = start_time + timedelta(minutes=minutes_after_start)

    amount = random.randint(200, 25000)

    method = random.choices(
        methods,
        weights=[50, 30, 15, 5],
        k=1
    )[0]

    # Normal baseline failure probability
    failure_probability = 0.08

    # Create a deliberate UPI failure spike between 8 PM and 10 PM.
    # This gives our AI something meaningful to discover.
    if (
        method == "UPI"
        and timestamp.hour >= 20
        and timestamp.hour < 22
    ):
        failure_probability = 0.38

    status = "Success"

    if random.random() < failure_probability:
        status = "Failed"

    failure_reason = ""

    if status == "Failed":
        failure_reason = random.choice(failure_reasons)

    rows.append([
        transaction_id,
        timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        amount,
        method,
        status,
        failure_reason,
    ])


with open("data/transactions.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    writer.writerow([
        "transaction_id",
        "timestamp",
        "amount",
        "payment_method",
        "status",
        "failure_reason",
    ])

    writer.writerows(rows)


print("✅ Transaction dataset created successfully!")
print("📊 Total transactions:", len(rows))
print("📁 Saved to: data/transactions.csv")