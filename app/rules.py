from app.schemas import Purchase, RefundDecision

TRIAL_AMOUNT_INR = 1
MONTHLY_AMOUNT_INR = 249
ANNUAL_AMOUNT_INR = 1499


def decide_refund(purchases: list[Purchase], app_opens_since_renewal: int) -> RefundDecision:
    renewals = [p for p in purchases if p.type == "renewal" and p.status == "successful"]
    failed = [p for p in purchases if p.status == "failed"]
    pending = [p for p in purchases if p.status == "initiated"]

    if not renewals:
        if pending:
            return RefundDecision(
                decision="review",
                amount_inr=0,
                reason="payment still initiated, not confirmed; route to billing",
            )
        return RefundDecision(
            decision="no_refund",
            amount_inr=0,
            reason="no successful renewal charge on record",
        )

    latest = renewals[-1]
    if app_opens_since_renewal == 0:
        return RefundDecision(
            decision="refund",
            amount_inr=latest.amount_inr,
            reason="renewal charged and app never opened since renewal",
        )
    return RefundDecision(
        decision="review",
        amount_inr=0,
        reason="renewal charged and app was used; needs human review",
    )