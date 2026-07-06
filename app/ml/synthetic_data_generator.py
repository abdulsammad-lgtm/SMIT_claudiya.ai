"""
Generates synthetic transaction data for training the XGBoost model.
Produces realistic fraud patterns: card testing, velocity bursts,
freight forwarding, chargeback history, etc.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from app.tools.fraud_patterns import (
    ML_FEATURE_NAMES,
    AVS_SCORE_MAP,
    MERCHANT_RISK_MULTIPLIERS,
    KNOWN_FREIGHT_FORWARDER_ZIPS,
    NEW_ACCOUNT_CONFIG,
)


RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)


def _random_timestamp() -> datetime:
    base = datetime(2025, 6, 1)
    offset = rng.integers(0, 90 * 86400)
    return base + timedelta(seconds=int(offset))


def _random_merchant_category() -> str:
    cats = list(MERCHANT_RISK_MULTIPLIERS.keys())
    return rng.choice(cats)


def _gen_legitimate() -> list:
    amount = rng.exponential(80) + 10
    return {
        "amount": round(amount, 2),
        "amount_log": np.log1p(amount),
        "hour_of_day": rng.integers(8, 22),
        "day_of_week": rng.integers(0, 4),
        "is_weekend": 0,
        "card_velocity_count": rng.integers(0, 2),
        "ip_velocity_count": rng.integers(0, 2),
        "user_velocity_count": rng.integers(0, 3),
        "avs_code_encoded": float(AVS_SCORE_MAP.get(rng.choice(["Y", "Y", "Y", "A", "Z"]), 0)),
        "cvv_missing": 0.0,
        "billing_shipping_country_match": 1.0,
        "billing_shipping_zip_match": 1.0 if rng.random() > 0.1 else 0.0,
        "is_freight_forwarder": 0.0,
        "bin_country_match": 1.0,
        "is_vpn": 0.0,
        "is_proxy": 0.0,
        "is_prepaid_card": 0.0,
        "merchant_risk_multiplier": MERCHANT_RISK_MULTIPLIERS.get(_random_merchant_category(), 1.0),
        "account_age_days": rng.integers(30, 365 * 3),
        "chargeback_count_90d": 0.0,
        "return_rate": rng.beta(1, 20),
        "total_orders": rng.integers(5, 50),
        "is_new_account": 0.0,
        "amount_vs_user_avg_ratio": rng.uniform(0.3, 2.0),
        "is_micro_transaction": 0.0,
        "fraud_label": 0,
    }


def _gen_fraud_card_testing() -> list:
    amount = rng.uniform(200, 800)
    return {
        "amount": round(amount, 2),
        "amount_log": np.log1p(amount),
        "hour_of_day": rng.integers(0, 6),
        "day_of_week": rng.integers(5, 7),
        "is_weekend": 1,
        "card_velocity_count": rng.integers(5, 15),
        "ip_velocity_count": rng.integers(3, 8),
        "user_velocity_count": rng.integers(1, 4),
        "avs_code_encoded": float(AVS_SCORE_MAP.get(rng.choice(["N", "N", "Z"]), 3)),
        "cvv_missing": 1.0 if rng.random() > 0.3 else 0.0,
        "billing_shipping_country_match": 0.0 if rng.random() > 0.2 else 1.0,
        "billing_shipping_zip_match": 0.0,
        "is_freight_forwarder": 0.0,
        "bin_country_match": 0.0 if rng.random() > 0.3 else 0.5,
        "is_vpn": 1.0 if rng.random() > 0.5 else 0.0,
        "is_proxy": 1.0 if rng.random() > 0.7 else 0.0,
        "is_prepaid_card": 1.0 if rng.random() > 0.6 else 0.0,
        "merchant_risk_multiplier": MERCHANT_RISK_MULTIPLIERS.get("electronics", 1.4),
        "account_age_days": rng.integers(0, 10),
        "chargeback_count_90d": 0.0,
        "return_rate": 0.0,
        "total_orders": rng.integers(0, 3),
        "is_new_account": 1.0,
        "amount_vs_user_avg_ratio": 5.0,
        "is_micro_transaction": 0.0,
        "fraud_label": 1,
    }


def _gen_fraud_freight_forwarder() -> list:
    amount = rng.uniform(300, 1500)
    return {
        "amount": round(amount, 2),
        "amount_log": np.log1p(amount),
        "hour_of_day": rng.integers(9, 17),
        "day_of_week": rng.integers(0, 6),
        "is_weekend": 0,
        "card_velocity_count": rng.integers(0, 2),
        "ip_velocity_count": rng.integers(0, 2),
        "user_velocity_count": rng.integers(0, 2),
        "avs_code_encoded": float(AVS_SCORE_MAP.get(rng.choice(["Y", "A"]), 0)),
        "cvv_missing": 0.0,
        "billing_shipping_country_match": 1.0,
        "billing_shipping_zip_match": 1.0,
        "is_freight_forwarder": 1.0,
        "bin_country_match": 1.0,
        "is_vpn": 0.0,
        "is_proxy": 0.0,
        "is_prepaid_card": 0.0,
        "merchant_risk_multiplier": MERCHANT_RISK_MULTIPLIERS.get("electronics", 1.4),
        "account_age_days": rng.integers(60, 365),
        "chargeback_count_90d": 0.0,
        "return_rate": rng.beta(1, 10),
        "total_orders": rng.integers(3, 20),
        "is_new_account": 0.0,
        "amount_vs_user_avg_ratio": rng.uniform(1.0, 3.0),
        "is_micro_transaction": 0.0,
        "fraud_label": 1,
    }


def _gen_fraud_chargeback_abuse() -> list:
    amount = rng.uniform(50, 300)
    return {
        "amount": round(amount, 2),
        "amount_log": np.log1p(amount),
        "hour_of_day": rng.integers(10, 20),
        "day_of_week": rng.integers(0, 5),
        "is_weekend": 0,
        "card_velocity_count": rng.integers(1, 3),
        "ip_velocity_count": rng.integers(0, 2),
        "user_velocity_count": rng.integers(1, 4),
        "avs_code_encoded": float(AVS_SCORE_MAP.get("Y", 0)),
        "cvv_missing": 0.0,
        "billing_shipping_country_match": 1.0,
        "billing_shipping_zip_match": 1.0,
        "is_freight_forwarder": 0.0,
        "bin_country_match": 1.0,
        "is_vpn": 0.0,
        "is_proxy": 0.0,
        "is_prepaid_card": 0.0,
        "merchant_risk_multiplier": 1.0,
        "account_age_days": rng.integers(30, 200),
        "chargeback_count_90d": float(rng.integers(2, 8)),
        "return_rate": rng.uniform(0.3, 0.7),
        "total_orders": rng.integers(5, 30),
        "is_new_account": 0.0,
        "amount_vs_user_avg_ratio": rng.uniform(0.5, 1.5),
        "is_micro_transaction": 0.0,
        "fraud_label": 1,
    }


def generate_synthetic_dataset(n_samples: int = 10000) -> pd.DataFrame:
    fraud_pct = 0.15
    n_fraud = int(n_samples * fraud_pct)
    n_legit = n_samples - n_fraud

    records = [_gen_legitimate() for _ in range(n_legit)]
    n_card_testing = int(n_fraud * 0.4)
    n_freight = int(n_fraud * 0.3)
    n_chargeback = n_fraud - n_card_testing - n_freight

    records.extend([_gen_fraud_card_testing() for _ in range(n_card_testing)])
    records.extend([_gen_fraud_freight_forwarder() for _ in range(n_freight)])
    records.extend([_gen_fraud_chargeback_abuse() for _ in range(n_chargeback)])

    df = pd.DataFrame(records)
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)
    return df
