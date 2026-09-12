import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
    confusion_matrix
)


DATA_FILE = "data/transactions.csv"


def evaluate_model():

    # -----------------------------------------
    # LOAD DATA
    # -----------------------------------------

    df = pd.read_csv(DATA_FILE)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"]
    )

    # -----------------------------------------
    # CREATE FEATURES
    # -----------------------------------------

    df["hour"] = df["timestamp"].dt.hour

    df["day_of_week"] = (
        df["timestamp"].dt.dayofweek
    )

    features = [
        "amount",
        "payment_method",
        "hour",
        "day_of_week"
    ]

    X = df[features]

    # Success = 1
    # Failure = 0
    y = (
        df["status"]
        .astype(str)
        .str.lower()
        .eq("success")
        .astype(int)
    )

    # -----------------------------------------
    # TRAIN / TEST SPLIT
    # -----------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    # -----------------------------------------
    # PREPROCESSING
    # -----------------------------------------

    numeric_features = [
        "amount",
        "hour",
        "day_of_week"
    ]

    categorical_features = [
        "payment_method"
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
                categorical_features
            ),
            (
                "numeric",
                "passthrough",
                numeric_features
            )
        ]
    )

    # -----------------------------------------
    # MODEL
    # -----------------------------------------

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced"
    )

    pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor
            ),
            (
                "model",
                model
            )
        ]
    )

    # -----------------------------------------
    # TRAIN
    # -----------------------------------------

    pipeline.fit(
        X_train,
        y_train
    )

    # -----------------------------------------
    # PREDICTIONS
    # -----------------------------------------

    predictions = pipeline.predict(
        X_test
    )

    probabilities = pipeline.predict_proba(
        X_test
    )[:, 1]

    # -----------------------------------------
    # METRICS
    # -----------------------------------------

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0
    )

    roc_auc = roc_auc_score(
        y_test,
        probabilities
    )

    matrix = confusion_matrix(
        y_test,
        predictions
    )

    # -----------------------------------------
    # OUTPUT
    # -----------------------------------------

    print()
    print("=" * 50)
    print("REVENUE RESCUE AI - ML EVALUATION")
    print("=" * 50)

    print()
    print("Dataset")
    print("-" * 50)

    print(
        f"Total transactions: {len(df)}"
    )

    print(
        f"Training transactions: {len(X_train)}"
    )

    print(
        f"Test transactions: {len(X_test)}"
    )

    print()
    print("Features")
    print("-" * 50)

    for feature in features:
        print(f"- {feature}")

    print()
    print("Model")
    print("-" * 50)

    print(
        "RandomForestClassifier"
    )

    print()
    print("Performance")
    print("-" * 50)

    print(
        f"Accuracy : {accuracy:.4f} "
        f"({accuracy * 100:.2f}%)"
    )

    print(
        f"Precision: {precision:.4f} "
        f"({precision * 100:.2f}%)"
    )

    print(
        f"Recall   : {recall:.4f} "
        f"({recall * 100:.2f}%)"
    )

    print(
        f"ROC-AUC  : {roc_auc:.4f}"
    )

    print()
    print("Confusion Matrix")
    print("-" * 50)

    print(matrix)

    print()
    print("=" * 50)
    print("EVALUATION COMPLETE")
    print("=" * 50)
    print()


if __name__ == "__main__":
    evaluate_model()