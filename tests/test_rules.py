from app.rules import decide_refund
from app.schemas import Purchase


def test_renewal_never_opened_is_refunded():
    # T-1001: renewal charged, app never opened
    purchases = [
        Purchase(id="pay_A1", type="trial", amount_inr=1, status="successful", at="2026-08-31T20:02:00+05:30"),
        Purchase(id="pay_A2", type="renewal", amount_inr=249, status="successful", at="2026-09-01T20:04:00+05:30"),
    ]
    result = decide_refund(purchases, app_opens_since_renewal=0)
    assert result.decision == "refund"
    assert result.amount_inr == 249


def test_renewal_used_app_goes_to_review():
    # T-1002: renewal charged, app used 41 times
    purchases = [
        Purchase(id="pay_B4", type="renewal", amount_inr=249, status="successful", at="2026-08-15T10:29:00+05:30"),
    ]
    result = decide_refund(purchases, app_opens_since_renewal=41)
    assert result.decision == "review"
    assert result.amount_inr == 0


def test_initiated_renewal_goes_to_review():
    # T-1005: renewal still initiated, not confirmed
    purchases = [
        Purchase(id="pay_E2", type="renewal", amount_inr=249, status="initiated", at="2026-09-03T19:45:00+05:30"),
    ]
    result = decide_refund(purchases, app_opens_since_renewal=6)
    assert result.decision == "review"
    assert result.amount_inr == 0


def test_failed_then_successful_is_not_a_double_charge():
    # T-1009: first payment failed, second successful
    purchases = [
        Purchase(id="pay_I1", type="renewal", amount_inr=249, status="failed", at="2026-09-05T06:00:00+05:30"),
        Purchase(id="pay_I2", type="renewal", amount_inr=249, status="successful", at="2026-09-05T06:03:00+05:30"),
    ]
    result = decide_refund(purchases, app_opens_since_renewal=3)
    assert result.decision == "no_refund"
    assert result.amount_inr == 0