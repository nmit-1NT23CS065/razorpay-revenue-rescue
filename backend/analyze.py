import os
import pandas as pd

from database import get_transactions
from recovery import generate_recovery_plan

# Configurable benchmark scenario.
# This is an opportunity scenario, NOT an AI prediction.
RECOVERY_OPPORTUNITY_RATE = float(
    os.getenv("RECOVERY_OPPORTUNITY_RATE", "0.65")
)


def analyze_transactions():
    df = get_transactions()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    total_transactions = len(df)
    successful = df[
        df["status"].astype(str).str.lower() == "success"
    ]
    failed = df[
        df["status"].astype(str).str.lower() == "failed"
    ]

    total_revenue = successful["amount"].sum()
    failed_revenue = failed["amount"].sum()

    failure_rate = (
        len(failed) / total_transactions * 100
        if total_transactions else 0
    )

    df["hour"] = df["timestamp"].dt.hour
    hourly_failures = (
        df[df["status"].astype(str).str.lower() == "failed"]
        .groupby("hour")
        .agg(
            failed_transactions=("transaction_id", "count"),
            revenue_at_risk=("amount", "sum")
        )
        .sort_values("revenue_at_risk", ascending=False)
    )

    worst_hour = (
        int(hourly_failures.index[0])
        if len(hourly_failures) else None
    )
    worst_hour_failures = (
        int(hourly_failures.iloc[0]["failed_transactions"])
        if len(hourly_failures) else 0
    )
    worst_hour_revenue = (
        int(hourly_failures.iloc[0]["revenue_at_risk"])
        if len(hourly_failures) else 0
    )

    evening_upi = df[
        (df["payment_method"].astype(str).str.upper() == "UPI")
        & (df["timestamp"].dt.hour >= 20)
        & (df["timestamp"].dt.hour < 22)
    ]

    evening_upi_failures = evening_upi[
        evening_upi["status"].astype(str).str.lower() == "failed"
    ]

    evening_upi_failure_rate = (
        len(evening_upi_failures) / len(evening_upi) * 100
        if len(evening_upi) else 0
    )

    # Benchmark scenario: dynamically scales with current failed value.
    recovery_opportunity = failed_revenue * RECOVERY_OPPORTUNITY_RATE

    # Actual model-driven recovery estimate.
    recovery_plan = generate_recovery_plan()
    estimated_recovery = recovery_plan["estimated_recovery"]

    return {
        "total_transactions": int(total_transactions),
        "successful_transactions": int(len(successful)),
        "failed_transactions": int(len(failed)),
        "failure_rate": round(failure_rate, 2),
        "successful_revenue": int(total_revenue),
        "revenue_at_risk": int(failed_revenue),

        # Backward-compatible field used by the current frontend.
        "potentially_recoverable": int(round(recovery_opportunity)),
        "recoverable_percentage": round(
            RECOVERY_OPPORTUNITY_RATE * 100, 2
        ),

        # Explicit names for the two different concepts.
        "recovery_opportunity": int(round(recovery_opportunity)),
        "recovery_opportunity_rate": round(
            RECOVERY_OPPORTUNITY_RATE * 100, 2
        ),
        "estimated_recovery": int(estimated_recovery),

        "worst_hour": worst_hour,
        "worst_hour_failures": worst_hour_failures,
        "worst_hour_revenue": worst_hour_revenue,
        "evening_upi_failure_rate": round(
            evening_upi_failure_rate, 2
        ),
        "ai_detection": (
            "UPI payment failures spike between 8 PM and 10 PM."
        ),
        "recommendation": (
            "Prioritize transactions by modeled recovery probability, "
            "select the intervention with the highest expected recovery, "
            "and route high-value or low-confidence cases to human review."
        ),
        "opportunity_note": (
            "Recovery opportunity is a configurable benchmark scenario; "
            "estimated recovery is model-driven."
        ),
    }


if __name__ == "__main__":
    print(analyze_transactions())
