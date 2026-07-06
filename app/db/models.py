import os
import enum
import datetime

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Float, DateTime, Text, Integer, Boolean, Enum as SAEnum

from app.core.config import get_settings

_settings = get_settings()

def _build_engine():
    url = _settings.database_url
    use_sqlite = "sqlite" in url
    if use_sqlite and "aiosqlite" not in url:
        url = url.replace("postgresql+asyncpg://", "sqlite+aiosqlite://")
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fraud_demo.db"
        )
        url = f"sqlite+aiosqlite:///{db_path}"
    elif not use_sqlite and "postgresql" in url and "+" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    connect_args = {"check_same_thread": False} if use_sqlite else {}
    return create_async_engine(url, echo=False, connect_args=connect_args)

engine = _build_engine()
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class DecisionEnum(str, enum.Enum):
    approve = "approve"
    review = "review"
    decline = "decline"


class PaymentMethodEnum(str, enum.Enum):
    card = "card"
    cod = "cod"
    wallet = "wallet"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, unique=True, nullable=False, index=True)
    customer_id = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    payment_method = Column(String, nullable=False)
    device_fingerprint = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    shipping_address = Column(Text, nullable=False)
    user_agent = Column(String, nullable=False)
    session_duration_seconds = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    card_bin = Column(String, default="")
    card_last4 = Column(String, default="")
    cvv_provided = Column(Integer, default=0)
    avs_result = Column(String, default="U")
    billing_address = Column(Text, default="")
    billing_country = Column(String, default="")
    billing_zip = Column(String, default="")
    shipping_country = Column(String, default="")
    shipping_zip = Column(String, default="")
    merchant_id = Column(String, default="")
    merchant_category = Column(String, default="default")

    decision = Column(String, default="pending")
    risk_score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    agent_scores_json = Column(Text, nullable=True)
    reason_codes_json = Column(Text, nullable=True)
    latency_ms = Column(Float, nullable=True)
    scoring_path = Column(String, default="fast")
    device_ip_country = Column(String, nullable=True)
    device_is_vpn = Column(Integer, nullable=True)
    device_is_proxy = Column(Integer, nullable=True)
    device_enriched = Column(Integer, default=0)
    overridden = Column(Integer, default=0)
    override_decision = Column(String, nullable=True)
    override_by = Column(String, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    previous_decision = Column(String, nullable=True)
    new_decision = Column(String, nullable=True)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="analyst")
    disabled = Column(Boolean, default=False)
    api_key = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    trust_tier = Column(String, default="standard")
    total_orders = Column(Integer, default=0)
    return_count = Column(Integer, default=0)


class Chargeback(Base):
    __tablename__ = "chargebacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    order_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class FraudLabel(Base):
    __tablename__ = "fraud_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String, nullable=False, index=True)
    label = Column(String, nullable=False)
    source = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class BINCache(Base):
    __tablename__ = "bin_cache"

    bin = Column(String, primary_key=True)
    data_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
