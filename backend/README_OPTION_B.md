# Revenue Rescue AI — Option B Recovery Model

## What changed

The old recovery score used manually assigned points such as:
- base score = 50
- bank timeout = +25
- UPI = +5
- amount <= 10,000 = +10

Those are no longer used.

## New scoring strategy

The recovery model is an action-conditional Random Forest.

Training features:
- amount
- payment_method
- failure_reason
- hour
- day_of_week
- action

Target:
- recovered (0/1)

For every failed transaction the model evaluates:
- P(recovery | transaction, RETRY)
- P(recovery | transaction, SEND_REMINDER)

Recovery Score:
    selected recovery probability × 100

Decision:
1. If amount > ₹50,000 -> HUMAN_REVIEW (hard safety policy)
2. Otherwise compare modeled expected recovery for RETRY vs REMINDER.
3. If both modeled probabilities are below 50%, -> HUMAN_REVIEW.
4. Otherwise choose the action with the higher modeled probability.

The 50% threshold is a neutral probability cutoff: with equal costs,
a probability above 0.50 means recovery is more likely than non-recovery.

Expected recovery:
    amount × selected recovery probability

## Important prototype limitation

The current transaction database does not contain historical intervention
outcomes (for example, "failed -> retry -> recovered"). Therefore a genuine
recovery model cannot be trained from the current data alone.

For this buildathon prototype, the model-training labels are generated from
transparent, documented synthetic benchmark assumptions. This demonstrates
the correct architecture without pretending the assumptions are real Razorpay
recovery data.

Production version:
- ingest real failed-payment events
- record which intervention was taken
- record whether the payment recovered
- train/calibrate on those real outcomes
- continuously evaluate calibration and business lift

## 65% recovery opportunity

The dashboard opportunity number remains a configurable scenario:
RECOVERY_OPPORTUNITY_RATE, default 0.65.

It is NOT the AI's predicted recovery rate.

Set it with:
RECOVERY_OPPORTUNITY_RATE=0.60
(or another approved scenario value)

The model-driven estimated recovery is a separate metric.
