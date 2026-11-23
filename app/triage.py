import logging

from app.llm import call_model
from app.rules import decide_refund
from app.schemas import RefundDecision, TicketIn, TriageResult
from app.store import TriageStore
from app.validate import get_validated_output

log = logging.getLogger("triage")

FALLBACK_REPLY = "Thanks for writing in. A team member will get back to you shortly."
CONFIDENCE_FLOOR = 0.6

FRAUD_WORDS = (
    "fraud", "cyber cell", "never installed", "did not sign up",
    "didn't sign up", "unauthorised", "unauthorized",
)


def looks_like_fraud(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in FRAUD_WORDS)


def run_triage(ticket: TicketIn, store: TriageStore) -> TriageResult:
    # 1. Same ticket again: return the saved result, call nothing.
    saved = store.get(ticket.id)
    if saved is not None:
        return saved

    # 2. Money comes from the rules, computed before the model is called.
    refund = decide_refund(ticket.purchases, ticket.app_opens_since_renewal)

    # 3. The model suggests category, severity and reply. It cannot touch refund.
    text = f"{ticket.subject}\n{ticket.body}"
    model_out = get_validated_output(call_model, text)

    # Fraud claims are never auto-refunded. This can only make a decision more careful.
    fraud_claim = looks_like_fraud(text) or (
        model_out is not None and model_out.category == "security_fraud"
    )
    if fraud_claim and refund.decision == "refund":
        refund = RefundDecision(
            decision="review",
            amount_inr=0,
            reason="fraud or unauthorised charge claimed; never auto-refund",
        )

    if model_out is None:
        # 4a. Model failed twice: keep the rules' refund, send to a human.
        result = TriageResult(
            ticket_id=ticket.id,
            category="other",
            severity="medium",
            refund=refund,
            reply_draft=FALLBACK_REPLY,
            needs_human=True,
            confidence=0.0,
            source="fallback",
        )
    else:
        # 4b. Model answered: a human is needed if the rules or the model are unsure.
        needs_human = refund.decision == "review" or model_out.confidence < CONFIDENCE_FLOOR
        result = TriageResult(
            ticket_id=ticket.id,
            category=model_out.category,
            severity=model_out.severity,
            refund=refund,
            reply_draft=model_out.reply_draft,
            needs_human=needs_human,
            confidence=model_out.confidence,
            source="model",
        )

    # 5. Save first, so a repeat never runs the model again.
    store.save(result)

    # 6. Log only IDs and decisions. No message text, no names, no contact details.
    log.info(
        "ticket=%s category=%s refund=%s needs_human=%s source=%s",
        result.ticket_id, result.category.value, result.refund.decision,
        result.needs_human, result.source,
    )
    return result