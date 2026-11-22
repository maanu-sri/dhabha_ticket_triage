from app.schemas import RefundDecision, TriageResult
from app.store import TriageStore


def make_result(ticket_id, amount):
    return TriageResult(
        ticket_id=ticket_id,
        category="refund_request",
        severity="high",
        refund=RefundDecision(decision="refund", amount_inr=amount, reason="test"),
        reply_draft="Hi",
        needs_human=False,
        confidence=0.9,
        source="rules",
    )


def test_second_save_does_not_change_result(tmp_path):
    store = TriageStore(tmp_path / "test.db")
    store.save(make_result("T-1003", 249))
    store.save(make_result("T-1003", 1499))
    saved = store.get("T-1003")
    assert saved.refund.amount_inr == 249


def test_unknown_ticket_returns_none(tmp_path):
    store = TriageStore(tmp_path / "test.db")
    assert store.get("T-9999") is None