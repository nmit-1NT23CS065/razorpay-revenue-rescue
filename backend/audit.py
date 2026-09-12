import json
import os
from datetime import datetime


AUDIT_FILE = "data/audit_log.json"


def ensure_audit_file():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(AUDIT_FILE):
        with open(AUDIT_FILE, "w") as f:
            json.dump([], f)


def log_event(
    event_type,
    transaction_id=None,
    action=None,
    amount=None,
    score=None,
    reason=None,
    result=None,
    ml_success_probability=None
):
    ensure_audit_file()

    with open(AUDIT_FILE, "r") as f:
        logs = json.load(f)

    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "transaction_id": transaction_id,
        "action": action,
        "amount": amount,
        "recovery_score": score,
        "ml_success_probability": ml_success_probability,
        "reason": reason,
        "result": result
    }

    logs.append(event)

    with open(AUDIT_FILE, "w") as f:
        json.dump(logs, f, indent=2)

    return event


def get_audit_log():
    ensure_audit_file()

    with open(AUDIT_FILE, "r") as f:
        return json.load(f)