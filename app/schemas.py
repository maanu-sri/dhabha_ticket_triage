from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Category(str, Enum):
    refund_request = "refund_request"
    billing_issue = "billing_issue"
    payment_pending = "payment_pending"
    technical_bug = "technical_bug"
    account_access = "account_access"
    cancellation = "cancellation"
    invoice_request = "invoice_request"
    feature_request = "feature_request"
    pre_sales = "pre_sales"
    security_fraud = "security_fraud"
    other = "other"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Purchase(BaseModel):
    id: str
    type: Literal["trial", "renewal"]
    amount_inr: int = Field(ge=0)
    status: Literal["initiated", "failed", "successful", "renewal"]
    at: str


class TicketIn(BaseModel):
    id: str
    received_at: str
    subject: str
    body: str
    purchases: list[Purchase] = Field(default_factory=list)
    app_opens_since_renewal: int = Field(ge=0)


class ModelOutput(BaseModel):
    category: Category
    severity: Severity
    reply_draft: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class RefundDecision(BaseModel):
    decision: Literal["refund", "no_refund", "review"]
    amount_inr: int = Field(ge=0)
    reason: str


class TriageResult(BaseModel):
    ticket_id: str
    category: Category
    severity: Severity
    refund: RefundDecision
    reply_draft: str
    needs_human: bool
    confidence: float = Field(ge=0, le=1)
    source: Literal["model", "fallback", "rules"]