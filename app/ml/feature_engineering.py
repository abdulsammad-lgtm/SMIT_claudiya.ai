import math
import asyncio
import datetime
from typing import Optional

from sqlalchemy import select, func

from app.db.models import async_session, Transaction, User, Chargeback
from app.tools.fraud_patterns import (
    AVS_SCORE_MAP,
    MERCHANT_RISK_MULTIPLIERS,
    CHARGEBACK_CONFIG,
    NEW_ACCOUNT_CONFIG,
    ML_FEATURE_NAMES,
    KNOWN_FREIGHT_FORWARDER_ZIPS,
    KNOWN_FREIGHT_FORWARDER_KEYWORDS,
)


async def compute_features(
    payload,
    velocity_counts: dict,
    bin_info: Optional[dict],
    preloaded_user: Optional[dict] = None,
    preloaded_chargeback: Optional[float] = None,
    preloaded_avg_amount: Optional[float] = None,
) -> list[float]:
    if preloaded_user is not None:
        user_data = preloaded_user
        chargeback_count = preloaded_chargeback or 0.0
        user_avg_amount = preloaded_avg_amount
    else:
        user_data, chargeback_count, user_avg_amount = await asyncio.gather(
            _get_user_data(payload.user_id),
            _get_chargeback_count(payload.user_id),
            _get_user_avg_amount(payload.user_id),
        )

    ts = payload.timestamp
    hour_of_day = ts.hour
    day_of_week = ts.weekday()
    is_weekend = 1 if day_of_week >= 5 else 0

    amount = payload.amount
    amount_log = math.log1p(amount)

    card_velocity_count = velocity_counts.get("card_velocity_count", 0)
    ip_velocity_count = velocity_counts.get("ip_velocity_count", 0)
    user_velocity_count = velocity_counts.get("user_velocity_count", 0)

    avs_code_encoded = float(AVS_SCORE_MAP.get(payload.avs_result.upper(), 1))

    cvv_missing = 0.0 if payload.cvv_provided else 1.0

    billing_shipping_country_match = (
        1.0 if payload.billing_country == payload.shipping_country else 0.0
    )
    billing_shipping_zip_match = (
        1.0 if payload.billing_zip == payload.shipping_zip else 0.0
    )

    addr_lower = payload.shipping_address.lower()
    is_freight_forwarder = 1.0 if (
        payload.shipping_zip in KNOWN_FREIGHT_FORWARDER_ZIPS
        or any(kw in addr_lower for kw in KNOWN_FREIGHT_FORWARDER_KEYWORDS)
    ) else 0.0

    if bin_info:
        bin_country = bin_info.get("country_code", "")
        is_prepaid = 1.0 if bin_info.get("card_type") == "prepaid" else 0.0
        if payload.is_vpn:
            bin_country_match = 0.5
        else:
            bin_country_match = 1.0 if (
                bin_country and bin_country == payload.ip_country
            ) else 0.0
    else:
        bin_country_match = 0.5
        is_prepaid = 0.0

    is_vpn = 1.0 if payload.is_vpn else 0.0
    is_proxy = 1.0 if payload.is_proxy else 0.0

    merchant_risk_multiplier = MERCHANT_RISK_MULTIPLIERS.get(
        payload.merchant_category.lower(),
        MERCHANT_RISK_MULTIPLIERS["default"]
    )

    if user_data:
        created_at = user_data.get("created_at")
        if created_at:
            if isinstance(created_at, datetime.datetime):
                created_at_naive = created_at.replace(tzinfo=None)
            else:
                created_at_naive = created_at
            account_age_days = (datetime.datetime.utcnow() - created_at_naive).days
        else:
            account_age_days = 0.0
        total_orders = float(user_data.get("total_orders") or 0)
        return_count = float(user_data.get("return_count") or 0)
        return_rate = (return_count / total_orders) if total_orders > 3 else 0.0
    else:
        account_age_days = 0.0
        total_orders = 0.0
        return_rate = 0.0

    is_new_account = 1.0 if account_age_days < NEW_ACCOUNT_CONFIG["age_days_threshold"] else 0.0

    if user_avg_amount and user_avg_amount > 0:
        amount_vs_user_avg_ratio = amount / user_avg_amount
    else:
        amount_vs_user_avg_ratio = 1.0

    is_micro_transaction = 1.0 if amount <= 1.00 else 0.0

    feature_vector = [
        amount,
        amount_log,
        float(hour_of_day),
        float(day_of_week),
        float(is_weekend),
        float(card_velocity_count),
        float(ip_velocity_count),
        float(user_velocity_count),
        avs_code_encoded,
        cvv_missing,
        billing_shipping_country_match,
        billing_shipping_zip_match,
        is_freight_forwarder,
        bin_country_match,
        is_vpn,
        is_proxy,
        is_prepaid,
        float(merchant_risk_multiplier),
        float(account_age_days),
        float(chargeback_count),
        return_rate,
        total_orders,
        is_new_account,
        amount_vs_user_avg_ratio,
        is_micro_transaction,
    ]

    assert len(feature_vector) == len(ML_FEATURE_NAMES), (
        f"Feature vector length mismatch: got {len(feature_vector)}, "
        f"expected {len(ML_FEATURE_NAMES)}"
    )

    return feature_vector


async def _get_user_data(user_id: str) -> Optional[dict]:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.username == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                return {
                    "created_at": user.created_at,
                    "trust_tier": user.trust_tier,
                    "total_orders": user.total_orders,
                    "return_count": user.return_count,
                }
            return None
    except Exception:
        return None


async def _get_chargeback_count(user_id: str) -> float:
    try:
        lookback = datetime.datetime.utcnow() - datetime.timedelta(days=CHARGEBACK_CONFIG["lookback_days"])
        async with async_session() as session:
            result = await session.execute(
                select(func.count()).select_from(
                    select(Chargeback).where(
                        Chargeback.user_id == user_id,
                        Chargeback.created_at >= lookback,
                    ).subquery()
                )
            )
            return float(result.scalar() or 0)
    except Exception:
        return 0.0


async def _get_user_avg_amount(user_id: str) -> Optional[float]:
    try:
        since = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        async with async_session() as session:
            result = await session.execute(
                select(func.avg(Transaction.amount)).where(
                    Transaction.customer_id == user_id,
                    Transaction.timestamp >= since,
                    Transaction.decision == "approve",
                )
            )
            avg = result.scalar()
            return float(avg) if avg else None
    except Exception:
        return None
