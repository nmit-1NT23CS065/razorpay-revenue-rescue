# Revenue Rescue AI — Dynamic Transaction Layer

This replaces the static `transactions.csv` read path with SQLite while
keeping the existing AI/recovery logic.

## What changes

`transactions.csv` -> initial seed only

`transactions.db` -> live source of truth

Flow:

Transaction ingestion
        ↓
SQLite database
        ↓
Analyze / Recovery Plan
        ↓
Random Forest + deterministic rules
        ↓
Safety checks
        ↓
Simulation + audit log

SQLite is appropriate for this prototype because Python includes the
`sqlite3` module and SQLite is a lightweight disk-based database.

## Files to copy

Copy these files into your existing `backend/` folder:

- `database.py`
- `analyze.py`
- `ml_model.py`
- `recovery.py`
- `main.py`

Keep:

- `audit.py`
- `safety.py`
- `evaluation.py`
- `generate_data.py`
- `recovery_model.joblib`

## First run

From the backend folder:

    .\venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

On startup, `database.py` creates:

    data/transactions.db

If the database is empty, it imports the existing
`data/transactions.csv` exactly once.

## Test dynamic ingestion

Open:

    http://127.0.0.1:8000/docs

Use `POST /api/transactions`.

Example:

    {
      "amount": 5000,
      "payment_method": "UPI",
      "status": "Failed",
      "failure_reason": "Bank timeout"
    }

The transaction ID is generated automatically.

Then call:

    GET /api/analyze

You should see the transaction count and failed-payment metrics update.

Then call:

    GET /api/recovery-plan

The new failed transaction is included in the AI decision queue and gets
a recovery score and recommended action.

## Important ML behavior

Adding a transaction does NOT retrain the model for every new event.

The current Random Forest is cached and scores new transactions immediately.

When enough new labeled outcomes exist, retraining can be explicitly
triggered with:

    POST /api/retrain-model

This avoids expensive retraining on every transaction.

## Razorpay production architecture

In a real Razorpay integration, a `payment.failed` webhook would be an
appropriate ingestion source. Razorpay documents webhooks as asynchronous
server-to-server notifications and specifically supports `payment.failed`.

For this buildathon prototype, the POST `/api/transactions` endpoint is
a safe local simulation of that ingestion layer. No live payment is
processed.
