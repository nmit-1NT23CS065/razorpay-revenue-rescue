import os
import joblib
import pandas as pd
import numpy as np

from functools import lru_cache
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier

from database import get_transactions

MODEL_FILE = "recovery_model.joblib"

FEATURES = [
    "amount",
    "payment_method",
    "failure_reason",
    "hour",
    "day_of_week",
    "action",
]


def _base_recovery_probability(row, action):
    """
    Prototype-only outcome generator.

    IMPORTANT:
    The current transaction DB has no historical intervention outcomes
    (failed -> retry/reminder -> recovered). Therefore a true recovery
    model cannot be trained from the available data yet.

    For the buildathon prototype, we create transparent synthetic labels
    from benchmark-style directional assumptions. These labels are only
    for demonstrating the end-to-end recovery-learning architecture.
    Production training must replace them with real merchant outcomes.
    """
    reason = str(row.get("failure_reason", "")).lower()
    method = str(row.get("payment_method", "")).lower()
    amount = float(row.get("amount", 0))

    # Directional benchmark assumptions for prototype label generation.
    # They are deliberately kept here, documented, and never presented
    # as learned facts about Razorpay.
    if "bank timeout" in reason:
        base = {"RETRY": 0.68, "SEND_REMINDER": 0.32}
    elif "network error" in reason:
        base = {"RETRY": 0.64, "SEND_REMINDER": 0.30}
    elif "authentication" in reason:
        base = {"RETRY": 0.28, "SEND_REMINDER": 0.42}
    elif "payment declined" in reason:
        base = {"RETRY": 0.20, "SEND_REMINDER": 0.38}
    elif "insufficient funds" in reason:
        base = {"RETRY": 0.10, "SEND_REMINDER": 0.48}
    else:
        base = {"RETRY": 0.35, "SEND_REMINDER": 0.35}

    p = base.get(action, 0.35)

    # Small, transparent directional effects for the prototype labels.
    if method == "upi":
        p += 0.03
    elif method == "card":
        p += 0.01

    if amount <= 10000:
        p += 0.04
    elif amount > 50000:
        p -= 0.05

    hour = pd.to_datetime(row["timestamp"]).hour
    if method == "upi" and 20 <= hour < 22:
        p -= 0.03

    return float(np.clip(p, 0.02, 0.95))


def _build_training_data():
    df = get_transactions().copy()
    if df.empty:
        return pd.DataFrame(), pd.Series(dtype=int)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek

    # Failed payments are the population for the recovery problem.
    failed = df[df["status"].astype(str).str.lower() == "failed"].copy()

    # If the DB contains too few failed rows, fall back to all rows so the
    # endpoint remains usable during development.
    if failed.empty:
        failed = df.copy()

    rows = []
    rng = np.random.default_rng(42)

    for _, row in failed.iterrows():
        if pd.isna(row["hour"]) or pd.isna(row["day_of_week"]):
            continue
        for action in ("RETRY", "SEND_REMINDER"):
            p = _base_recovery_probability(row, action)

            record = {
                "amount": float(row["amount"]),
                "payment_method": row["payment_method"],
                "failure_reason": row["failure_reason"],
                "hour": int(row["hour"]),
                "day_of_week": int(row["day_of_week"]),
                "action": action,
                "recovered": int(rng.random() < p),
            }
            rows.append(record)

    train = pd.DataFrame(rows)
    return train[FEATURES], train["recovered"]


def train_model():
    X, y = _build_training_data()

    if X.empty:
        raise ValueError("No transaction data available to train recovery model.")

    categorical_features = [
        "payment_method",
        "failure_reason",
        "action",
    ]
    numeric_features = [
        "amount",
        "hour",
        "day_of_week",
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                categorical_features,
            ),
            (
                "numeric",
                "passthrough",
                numeric_features,
            ),
        ]
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced",
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    pipeline.fit(X, y)
    joblib.dump(pipeline, MODEL_FILE)
    load_model.cache_clear()

    return {
        "model_file": MODEL_FILE,
        "training_rows": len(X),
        "features": FEATURES,
        "target": "recovered",
        "model": "RandomForestClassifier",
        "training_type": "prototype_synthetic_recovery_outcomes",
    }


@lru_cache(maxsize=1)
def load_model():
    if not os.path.exists(MODEL_FILE):
        train_model()
    return joblib.load(MODEL_FILE)


def predict_recovery_probabilities(rows):
    if not rows:
        return []

    model = load_model()
    records = []

    for row in rows:
        timestamp = pd.to_datetime(row["timestamp"])
        for action in ("RETRY", "SEND_REMINDER"):
            records.append({
                "amount": float(row["amount"]),
                "payment_method": row["payment_method"],
                "failure_reason": row["failure_reason"],
                "hour": timestamp.hour,
                "day_of_week": timestamp.dayofweek,
                "action": action,
            })

    input_data = pd.DataFrame(records)
    probabilities = model.predict_proba(input_data)[:, 1]

    output = []
    for i in range(len(rows)):
        output.append({
            "retry": float(probabilities[i * 2]),
            "reminder": float(probabilities[i * 2 + 1]),
        })

    return output


# Compatibility alias: older code can still call this name.
def predict_success_probabilities(rows):
    """
    Deprecated compatibility helper.

    The new recovery engine should use predict_recovery_probabilities().
    This returns the retry recovery probability so older callers do not
    crash while the backend is being upgraded.
    """
    return [
        item["retry"]
        for item in predict_recovery_probabilities(rows)
    ]


def predict_recovery_probability(row, action):
    result = predict_recovery_probabilities([row])[0]
    return result["retry"] if action == "RETRY" else result["reminder"]


if __name__ == "__main__":
    result = train_model()
    print("RECOVERY MODEL TRAINED")
    print("----------------------")
    print(f"Training rows: {result['training_rows']}")
    print(f"Features: {', '.join(result['features'])}")
    print(f"Target: {result['target']}")
    print(f"Saved to: {result['model_file']}")

