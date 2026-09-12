import pandas as pd

from database import get_transactions
from ml_model import predict_recovery_probabilities


AUTOMATION_MIN_PROBABILITY = 0.50
HIGH_VALUE_LIMIT = 50000


def determine_action(retry_probability, reminder_probability, amount):
    """
    Choose the intervention with the highest modeled expected recovery.

    The 0.50 cutoff is a neutral probability threshold: with equal
    benefit/cost assumptions, >50% means recovery is more likely than
    non-recovery. High-value transactions are always escalated by policy.
    """
    if amount > HIGH_VALUE_LIMIT:
        return "HUMAN_REVIEW"

    best_probability = max(retry_probability, reminder_probability)

    if best_probability < AUTOMATION_MIN_PROBABILITY:
        return "HUMAN_REVIEW"

    if retry_probability >= reminder_probability:
        return "RETRY"

    return "SEND_REMINDER"


def generate_recovery_plan():
    df = get_transactions().copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    failed = df[
        df["status"].astype(str).str.lower() == "failed"
    ].copy()

    if failed.empty:
        return {
            "total_failed_transactions": 0,
            "total_failed_value": 0,
            "retry_count": 0,
            "retry_value": 0,
            "reminder_count": 0,
            "reminder_value": 0,
            "human_review_count": 0,
            "human_review_value": 0,
            "estimated_recovery": 0,
            "top_candidates": [],
            "all_decisions": [],
            "ml_enabled": True,
            "ml_model": "RandomForestClassifier",
            "ml_target": "recovered",
            "ml_features": [
                "amount", "payment_method", "failure_reason",
                "hour", "day_of_week", "action"
            ],
        }

    rows = [row for _, row in failed.iterrows()]
    probabilities = predict_recovery_probabilities(rows)

    failed["retry_recovery_probability"] = [
        p["retry"] for p in probabilities
    ]
    failed["reminder_recovery_probability"] = [
        p["reminder"] for p in probabilities
    ]

    failed["recommended_action"] = [
        determine_action(
            p["retry"],
            p["reminder"],
            float(row["amount"]),
        )
        for (_, row), p in zip(failed.iterrows(), probabilities)
    ]

    # Recovery Score is now the model's probability of successful recovery
    # under the selected action, expressed on a 0-100 scale.
    failed["recovery_probability"] = [
        (
            p["retry"]
            if action == "RETRY"
            else p["reminder"]
            if action == "SEND_REMINDER"
            else max(p["retry"], p["reminder"])
        )
        for p, action in zip(
            probabilities, failed["recommended_action"]
        )
    ]
    failed["recovery_score"] = failed["recovery_probability"] * 100

    # Expected recovered value is probability × amount for automated actions.
    failed["expected_recovery_value"] = [
        (
            p["retry"] * float(row["amount"])
            if action == "RETRY"
            else p["reminder"] * float(row["amount"])
            if action == "SEND_REMINDER"
            else 0.0
        )
        for (_, row), p, action in zip(
            failed.iterrows(),
            probabilities,
            failed["recommended_action"],
        )
    ]

    retry = failed[failed["recommended_action"] == "RETRY"]
    reminders = failed[
        failed["recommended_action"] == "SEND_REMINDER"
    ]
    human_review = failed[
        failed["recommended_action"] == "HUMAN_REVIEW"
    ]

    retry_value = retry["amount"].sum()
    reminder_value = reminders["amount"].sum()
    review_value = human_review["amount"].sum()
    total_failed_value = failed["amount"].sum()

    estimated_recovery = failed["expected_recovery_value"].sum()

    top_candidates = (
        failed.sort_values(
            ["recovery_score", "amount"],
            ascending=[False, False],
        ).head(10)
    )

    def serialize(row):
        action = row["recommended_action"]
        selected_probability = (
            row["retry_recovery_probability"]
            if action == "RETRY"
            else row["reminder_recovery_probability"]
            if action == "SEND_REMINDER"
            else max(
                row["retry_recovery_probability"],
                row["reminder_recovery_probability"],
            )
        )

        return {
            "transaction_id": row["transaction_id"],
            "amount": int(row["amount"]),
            "payment_method": row["payment_method"],
            "failure_reason": row["failure_reason"],
            "recovery_score": round(float(row["recovery_score"]), 2),
            "recovery_probability": round(
                float(selected_probability), 4
            ),
            "retry_recovery_probability": round(
                float(row["retry_recovery_probability"]), 4
            ),
            "reminder_recovery_probability": round(
                float(row["reminder_recovery_probability"]), 4
            ),
            "recommended_action": action,
            "expected_recovery_value": round(
                float(row["expected_recovery_value"]), 2
            ),
        }

    return {
        "total_failed_transactions": int(len(failed)),
        "total_failed_value": int(total_failed_value),
        "retry_count": int(len(retry)),
        "retry_value": int(retry_value),
        "reminder_count": int(len(reminders)),
        "reminder_value": int(reminder_value),
        "human_review_count": int(len(human_review)),
        "human_review_value": int(review_value),
        "estimated_recovery": int(round(estimated_recovery)),
        "top_candidates": [
            serialize(row) for _, row in top_candidates.iterrows()
        ],
        "all_decisions": [
            serialize(row) for _, row in failed.iterrows()
        ],
        "ml_enabled": True,
        "ml_model": "RandomForestClassifier",
        "ml_target": "recovered",
        "ml_features": [
            "amount",
            "payment_method",
            "failure_reason",
            "hour",
            "day_of_week",
            "action",
        ],
        "scoring_method": (
            "Recovery score = model-estimated recovery probability "
            "for the selected intervention × 100."
        ),
        "decision_method": (
            "Choose the highest modeled expected recovery among "
            "automated interventions; apply deterministic safety policies."
        ),
    }
