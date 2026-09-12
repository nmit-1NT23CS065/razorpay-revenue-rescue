MAX_AUTOMATED_RETRIES = 1

# Transactions above this amount always require
# human approval before recovery execution.
HIGH_VALUE_LIMIT = 50000

# Maximum percentage of failed transaction value that
# can be placed into an automated recovery campaign.
MAX_AUTOMATED_VALUE_PERCENT = 70


def check_transaction_safety(
    amount,
    action,
    previous_attempts=0
):
    """
    Apply transaction-level safety rules.
    """

    # High-value transactions require human review.
    if amount > HIGH_VALUE_LIMIT:
        return {
            "allowed": False,
            "action": "HUMAN_REVIEW",
            "reason": "Transaction exceeds automated recovery value limit."
        }

    # Never automatically retry more than once.
    if action == "RETRY":
        if previous_attempts >= MAX_AUTOMATED_RETRIES:
            return {
                "allowed": False,
                "action": "HUMAN_REVIEW",
                "reason": "Maximum automated retry limit reached."
            }

    return {
        "allowed": True,
        "action": action,
        "reason": "Transaction passed safety checks."
    }


def check_campaign_safety(
    automated_value,
    total_failed_value
):
    """
    Campaign-level stopping rule.

    Prevents the system from automatically acting on
    an excessive portion of the failed revenue.
    """

    if total_failed_value <= 0:
        return {
            "allowed": False,
            "reason": "No failed revenue available for recovery."
        }

    percentage = (
        automated_value
        / total_failed_value
    ) * 100

    if percentage > MAX_AUTOMATED_VALUE_PERCENT:
        return {
            "allowed": False,
            "reason": (
                "Automated recovery value exceeds "
                "campaign safety threshold."
            ),
            "automated_value_percent": round(
                percentage,
                2
            )
        }

    return {
        "allowed": True,
        "reason": "Campaign passed safety checks.",
        "automated_value_percent": round(
            percentage,
            2
        )
    }