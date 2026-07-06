import asyncio
from typing import Optional

from agents import Agent, Runner

from app.api.schemas import AgentScoreOutput
from app.db.models import Transaction
from app.tools.fraud_patterns import (
    VALID_FLAGS,
    SOFT_VELOCITY_THRESHOLDS,
    MERCHANT_RISK_MULTIPLIERS,
    HIGH_RISK_MERCHANT_THRESHOLD,
)
from app.tools.velocity_checker import (
    check_extreme_velocity,
    check_card_testing_hard_block,
    check_freight_forwarder_hard_block,
    check_cvv_avs_combined_hard_block,
    get_velocity_features,
)
from app.ml.feature_engineering import compute_features
from app.ml import model_inference as ml_inference
from app.ml.shap_explainer import explain
from app.tools.fraud_patterns import (
    _detect_card_testing,
    _detect_cod_ring,
    _detect_friendly_fraud,
    _detect_triangulation,
    score_fraud_patterns,
)
from app.tools.fraud_patterns import (
    detect_card_testing_pattern,
    detect_cod_fraud_ring,
    detect_friendly_fraud,
    detect_triangulation,
)
from app.tools.velocity_checker import (
    check_customer_velocity,
    check_device_velocity,
    check_ip_velocity,
    check_phone_velocity,
    compute_velocity_score,
)


class _Payload:
    """Lightweight payload wrapper for ML feature engineering."""
    def __init__(self, txn: Transaction, ip_country: str = "", is_vpn: bool = False, is_proxy: bool = False):
        self.transaction_id = txn.order_id
        self.user_id = txn.customer_id
        self.timestamp = txn.timestamp
        self.card_bin = txn.card_bin or ""
        self.card_last4 = txn.card_last4 or ""
        self.amount = txn.amount
        self.currency = txn.currency
        self.cvv_provided = bool(txn.cvv_provided)
        self.avs_result = txn.avs_result or "U"
        self.billing_address = txn.billing_address or ""
        self.billing_country = txn.billing_country or ""
        self.billing_zip = txn.billing_zip or ""
        self.shipping_address = txn.shipping_address
        self.shipping_country = txn.shipping_country or ""
        self.shipping_zip = txn.shipping_zip or ""
        self.merchant_id = txn.merchant_id or ""
        self.merchant_category = txn.merchant_category or "default"
        self.ip_address = txn.ip_address
        self.ip_country = ip_country
        self.is_vpn = is_vpn
        self.is_proxy = is_proxy


def compute_soft_flags(
    velocity_counts: dict,
    avs_result: str,
    billing_country: str,
    shipping_country: str,
) -> list[str]:
    flags = []
    cfg = SOFT_VELOCITY_THRESHOLDS
    if velocity_counts.get("card_velocity_count", 0) > cfg["card"]["max_attempts"]:
        flags.append("card_velocity_elevated")
    if velocity_counts.get("ip_velocity_count", 0) > cfg["ip"]["max_attempts"]:
        flags.append("ip_velocity_elevated")
    if velocity_counts.get("user_velocity_count", 0) > cfg["user"]["max_attempts"]:
        flags.append("user_velocity_elevated")
    if avs_result.upper() == "N":
        flags.append("avs_no_match")
    elif avs_result.upper() in ("Z", "A"):
        flags.append("avs_partial_match")
    if billing_country != shipping_country:
        flags.append("address_country_mismatch")
    return flags


async def fast_path_transaction(
    txn: Transaction,
    ip_country: str = "",
    is_vpn: bool = False,
    is_proxy: bool = False,
) -> AgentScoreOutput:
    from app.services.bin_lookup import lookup_bin

    payload = _Payload(txn, ip_country, is_vpn, is_proxy)

    extreme_vel = await check_extreme_velocity(payload.card_bin, payload.card_last4)
    card_test = await check_card_testing_hard_block(payload.ip_address, payload.amount)
    freight = await check_freight_forwarder_hard_block(payload.shipping_zip, payload.shipping_address)
    cvv_avs = check_cvv_avs_combined_hard_block(payload.cvv_provided, payload.avs_result)

    hard_block_flag = None
    if extreme_vel:
        hard_block_flag = "hard_block_extreme_velocity"
    elif card_test:
        hard_block_flag = "hard_block_card_testing"
    elif freight:
        hard_block_flag = "hard_block_freight_forwarder"
    elif cvv_avs:
        hard_block_flag = "hard_block_cvv_and_avs_fail"

    if hard_block_flag:
        return AgentScoreOutput(
            score=100.0,
            confidence=0.99,
            explanation=f"hard block: {hard_block_flag}",
            evidence=[hard_block_flag],
        )

    velocity_counts, bin_info = await asyncio.gather(
        get_velocity_features(
            payload.card_bin, payload.card_last4,
            payload.ip_address, payload.user_id,
        ),
        lookup_bin(payload.card_bin),
    )

    feature_vector = await compute_features(payload, velocity_counts, bin_info)

    ml_result, shap_result = await asyncio.gather(
        ml_inference.predict(feature_vector),
        explain(feature_vector),
    )

    final_score = ml_result["ml_score"]
    ml_flag = ["ml_model_unavailable"] if not ml_inference.MODEL_AVAILABLE else []

    soft_flags = compute_soft_flags(
        velocity_counts,
        payload.avs_result,
        payload.billing_country,
        payload.shipping_country,
    )

    category = payload.merchant_category.lower()
    multiplier = MERCHANT_RISK_MULTIPLIERS.get(category, 1.0)
    category_flags = (
        ["high_risk_merchant_category"]
        if multiplier >= HIGH_RISK_MERCHANT_THRESHOLD
        else []
    )

    vpn_flags = ["vpn_detected"] if payload.is_vpn else []

    all_flags = list(set(soft_flags + category_flags + vpn_flags + ml_flag))
    all_flags = [f for f in all_flags if f in VALID_FLAGS]

    explanation_parts = []
    if all_flags:
        explanation_parts.append("flags: " + ", ".join(all_flags))
    if shap_result:
        top = shap_result["top_features"][:3]
        for feat in top:
            direction = "↑" if feat["contribution"] > 0 else "↓"
            explanation_parts.append(
                f"{feat['feature']}={feat['value']} {direction}{abs(feat['contribution']):.3f}"
            )
    explanation = "; ".join(explanation_parts) if explanation_parts else "clean"

    return AgentScoreOutput(
        score=float(final_score),
        confidence=0.90,
        explanation=explanation,
        evidence=all_flags,
    )


transaction_agent_instructions = (
    "You are a transaction fraud analyst. Analyze individual transactions for fraud signals including:\n"
    "- Card testing patterns (multiple small amounts from same device)\n"
    "- COD fraud rings (multiple customers sharing phone/address for COD orders)\n"
    "- Friendly fraud (COD refusal patterns)\n"
    "- Triangulation fraud (same device shipping to many addresses)\n"
    "- Velocity bursts (many orders in short time windows)\n"
    "Output a score 0-100, confidence 0-1, and a plain-language explanation."
)
transaction_agent = Agent(
    name="TransactionAgent",
    instructions=transaction_agent_instructions,
    model="gpt-4o-mini",
    tools=[
        detect_card_testing_pattern,
        detect_cod_fraud_ring,
        detect_friendly_fraud,
        detect_triangulation,
        check_customer_velocity,
        check_device_velocity,
        check_ip_velocity,
        check_phone_velocity,
    ],
    output_type=AgentScoreOutput,
)
