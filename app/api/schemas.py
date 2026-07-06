import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# Auth schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "analyst"


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TransactionIn(BaseModel):
    order_id: str
    customer_id: str
    amount: float
    currency: str = "USD"
    payment_method: Literal["card", "cod", "wallet"]
    device_fingerprint: str
    ip_address: str
    phone_number: str
    shipping_address: str
    user_agent: str
    session_duration_seconds: float
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    card_bin: str = ""
    card_last4: str = ""
    cvv_provided: bool = False
    avs_result: str = "U"
    billing_address: str = ""
    billing_country: str = ""
    billing_zip: str = ""
    shipping_country: str = ""
    shipping_zip: str = ""
    merchant_id: str = ""
    merchant_category: str = "default"


class TransactionDecision(BaseModel):
    order_id: str
    decision: Literal["approve", "review", "decline"]
    risk_score: float
    confidence: float
    agent_scores: dict[str, float]
    reason_codes: list[str]
    latency_ms: float


class AgentScoreOutput(BaseModel):
    score: float
    confidence: float
    explanation: str
    evidence: list[str] = []


class OverrideRequest(BaseModel):
    decision: Literal["approve", "decline"]
    reason: str = ""
    analyst: str = "dashboard-user"
