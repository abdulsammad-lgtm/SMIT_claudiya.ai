"""
Decision thresholds and scoring weights.
Tune these values — they are deliberately isolated here so a non-engineer
can adjust risk appetite without touching any implementation code.
"""

FAST_PATH_WEIGHTS = {
    "device": 0.20,
    "behavior": 0.25,
    "network": 0.25,
    "transaction": 0.15,
    "behavioral": 0.15,
}

RISK_THRESHOLDS = {
    "approve_upper": 30,
    "review_upper": 70,
}

BASE_CONFIDENCE = 0.85

TOOL_THRESHOLDS = {
    "device_fingerprint_reuse": {"low": 1, "medium": 3, "high": 5},
    "ip_geolocation_mismatch": {"low": 0.3, "medium": 0.5, "high": 0.8},
    "proxy_risk": {"low": 0.2, "medium": 0.5, "high": 0.8},
    "user_agent_anomaly": {"low": 0.3, "medium": 0.5, "high": 0.8},
    "order_velocity_1h": {"low": 3, "medium": 6, "high": 10},
    "order_velocity_24h": {"low": 5, "medium": 10, "high": 20},
    "session_anomaly": {"low": 0.3, "medium": 0.5, "high": 0.8},
    "cart_value_anomaly": {"low": 0.3, "medium": 0.5, "high": 0.8},
    "cod_refusal_rate": {"low": 0.2, "medium": 0.4, "high": 0.6},
    "network_component_size": {"low": 2, "medium": 4, "high": 7},
    "network_cod_density": {"low": 0.3, "medium": 0.5, "high": 0.8},

    # Transaction agent thresholds
    "card_testing_small_txn_count": {"low": 2, "medium": 5, "high": 10},
    "card_testing_amount": {"low": 10, "medium": 20, "high": 50},
    "cod_ring_linked_customers": {"low": 2, "medium": 4, "high": 8},
    "friendly_fraud_cod_orders": {"low": 2, "medium": 4, "high": 8},
    "triangulation_address_count": {"low": 2, "medium": 4, "high": 6},
    "velocity_burst_1h": {"low": 3, "medium": 6, "high": 12},
    "velocity_daily_24h": {"low": 8, "medium": 15, "high": 30},

    # Behavioral agent thresholds
    "login_ip_diversity": {"low": 2, "medium": 4, "high": 8},
    "login_ua_diversity": {"low": 1, "medium": 3, "high": 5},
    "session_duration_zscore": {"low": 1.0, "medium": 2.0, "high": 3.0},
    "amount_duration_ratio_deviation": {"low": 1.5, "medium": 3.0, "high": 5.0},
    "typing_biometric_risk": {"low": 20, "medium": 40, "high": 60},
    "mouse_behavioral_risk": {"low": 20, "medium": 40, "high": 60},
    "profile_stability": {"low": 70, "medium": 40, "high": 20},
}


def score_from_signal(value: float, threshold_key: str) -> float:
    thresholds = TOOL_THRESHOLDS.get(threshold_key, {})
    low = thresholds.get("low", 0)
    medium = thresholds.get("medium", 50)
    high = thresholds.get("high", 80)
    if value <= low:
        return 0.0
    elif value <= medium:
        return 20.0 + 30.0 * (value - low) / (medium - low)
    elif value <= high:
        return 50.0 + 30.0 * (value - medium) / (high - medium)
    else:
        return 80.0 + 20.0 * min((value - high) / (high or 1), 1.0)
