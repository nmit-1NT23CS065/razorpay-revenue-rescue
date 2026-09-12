from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import (
    initialize_database,
    get_transactions,
    insert_transaction,
    generate_transaction_id,
    database_summary,
)
from analyze import analyze_transactions
from recovery import generate_recovery_plan
from audit import log_event, get_audit_log
from safety import check_transaction_safety, check_campaign_safety
from ml_model import train_model


app = FastAPI(title="Revenue Rescue AI")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TransactionInput(BaseModel):
    transaction_id: Optional[str] = None
    timestamp: Optional[str] = None
    amount: float = Field(gt=0)
    payment_method: str
    status: str = "Failed"
    failure_reason: str = ""


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/")
def home():
    return {"message": "Revenue Rescue AI backend is running"}


@app.get("/api/analyze")
def analyze_revenue():
    return analyze_transactions()


@app.get("/api/recovery-plan")
def recovery_plan():
    return generate_recovery_plan()


@app.get("/api/transactions")
def list_transactions():
    df = get_transactions()

    # Keep API JSON-safe if SQLite contains blank/NaN-like values.
    df = df.astype(object).where(df.notna(), None)

    return {
        "transactions": df.to_dict(orient="records"),
        "summary": database_summary(),
    }


@app.post("/api/transactions")
def add_transaction(transaction: TransactionInput):
    transaction_id = (
        transaction.transaction_id
        or generate_transaction_id()
    )
    timestamp = transaction.timestamp or datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    try:
        created = insert_transaction(
            transaction_id=transaction_id,
            timestamp=timestamp,
            amount=transaction.amount,
            payment_method=transaction.payment_method,
            status=transaction.status,
            failure_reason=transaction.failure_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    log_event(
        event_type="TRANSACTION_INGESTED",
        transaction_id=transaction_id,
        amount=transaction.amount,
        reason="Transaction added to live transaction database.",
        result="INGESTED",
    )

    return {
        "status": "CREATED",
        "transaction": created,
        "summary": database_summary(),
    }


@app.post("/api/retrain-model")
def retrain_model():
    result = train_model()
    return {
        "status": "RETRAINED",
        **result,
    }


@app.post("/api/execute-recovery")
def execute_recovery():
    # IDEMPOTENCY CHECK
    existing_logs = get_audit_log()

    completed_campaigns = [
        event
        for event in existing_logs
        if event.get("event_type") == "RECOVERY_CAMPAIGN"
        and event.get("result") == "SIMULATION_COMPLETED"
    ]

    if completed_campaigns:
        latest_campaign = completed_campaigns[-1]

        return {
            "status": "ALREADY_EXECUTED",
            "message": "Recovery campaign has already been executed.",
            "retry_actions": 0,
            "reminders_sent": 0,
            "human_reviews": 0,
            "recovered_revenue": latest_campaign.get("amount", 0),
            "execution_mode": "SIMULATION",
            "safety_status": "LOCKED",
            "note": (
                "Duplicate execution prevented by "
                "idempotency protection."
            ),
        }

    plan = generate_recovery_plan()

    campaign_safety = check_campaign_safety(
        automated_value=plan["retry_value"],
        total_failed_value=plan["total_failed_value"],
    )

    if not campaign_safety["allowed"]:
        log_event(
            event_type="SAFETY_STOP",
            action="STOP_RECOVERY_CAMPAIGN",
            amount=plan["retry_value"],
            result=campaign_safety["reason"],
        )

        return {
            "status": "STOPPED",
            "message": "Recovery campaign stopped by safety controls.",
            "retry_actions": 0,
            "reminders_sent": 0,
            "human_reviews": plan["total_failed_transactions"],
            "recovered_revenue": 0,
            "execution_mode": "SIMULATION",
            "safety_status": "BLOCKED",
            "safety_reason": campaign_safety["reason"],
            "note": "No recovery actions were executed.",
        }

    executed_retries = 0
    executed_reminders = 0
    escalated_reviews = 0
    recovered_revenue = 0.0

    for decision in plan["all_decisions"]:
        transaction_id = decision["transaction_id"]
        amount = decision["amount"]
        action = decision["recommended_action"]
        score = decision["recovery_score"]
        reason = decision["failure_reason"]

        # The selected recovery probability is the ML-derived score.
        recovery_probability = decision.get(
            "recovery_probability", score / 100
        )

        safety_result = check_transaction_safety(
            amount=amount,
            action=action,
            previous_attempts=0,
        )

        if not safety_result["allowed"]:
            escalated_reviews += 1

            log_event(
                event_type="SAFETY_ESCALATION",
                transaction_id=transaction_id,
                action="HUMAN_REVIEW",
                amount=amount,
                score=score,
                ml_success_probability=recovery_probability,
                reason=safety_result["reason"],
                result="BLOCKED_BY_SAFETY_RULE",
            )
            continue

        if action == "RETRY":
            executed_retries += 1

            # Simulation uses the model's expected recovery value.
            expected_value = (
                amount * recovery_probability
            )
            recovered_revenue += expected_value

            log_event(
                event_type="RECOVERY_DECISION",
                transaction_id=transaction_id,
                action="RETRY",
                amount=amount,
                score=score,
                ml_success_probability=recovery_probability,
                reason=reason,
                result="SIMULATED_RETRY",
            )

        elif action == "SEND_REMINDER":
            executed_reminders += 1

            expected_value = (
                amount * recovery_probability
            )
            recovered_revenue += expected_value

            log_event(
                event_type="RECOVERY_DECISION",
                transaction_id=transaction_id,
                action="SEND_REMINDER",
                amount=amount,
                score=score,
                ml_success_probability=recovery_probability,
                reason=reason,
                result="SIMULATED_REMINDER",
            )

        else:
            escalated_reviews += 1

            log_event(
                event_type="RECOVERY_DECISION",
                transaction_id=transaction_id,
                action="HUMAN_REVIEW",
                amount=amount,
                score=score,
                ml_success_probability=recovery_probability,
                reason=reason,
                result="ESCALATED_FOR_HUMAN_REVIEW",
            )

    recovered_revenue = int(round(recovered_revenue))

    log_event(
        event_type="RECOVERY_CAMPAIGN",
        action="EXECUTE_RECOVERY_PLAN",
        amount=recovered_revenue,
        result="SIMULATION_COMPLETED",
    )

    return {
        "status": "EXECUTED",
        "message": "Recovery plan executed successfully.",
        "retry_actions": executed_retries,
        "reminders_sent": executed_reminders,
        "human_reviews": escalated_reviews,
        "recovered_revenue": recovered_revenue,
        "execution_mode": "SIMULATION",
        "safety_status": "PASSED",
        "automated_retry_value": int(plan["retry_value"]),
        "automated_value_percent": campaign_safety[
            "automated_value_percent"
        ],
        "note": (
            "No real payments were processed. Safety controls, "
            "model-derived expected recovery, stopping rules, and "
            "duplicate-execution protection were applied."
        ),
    }


@app.get("/api/audit-log")
def audit_log():
    return {"events": get_audit_log()}
