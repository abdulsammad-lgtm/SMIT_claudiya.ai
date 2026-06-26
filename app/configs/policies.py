from enum import Enum


class BiasDimension(str, Enum):
    GENDER = "gender"
    REGION = "region"
    PAYMENT_METHOD = "payment_method"
    DEVICE_TYPE = "device_type"
    CUSTOMER_TENURE = "customer_tenure"


BiasPolicy = {
    "protected_attributes": ["shipping_region", "payment_method", "device_type"],
    "disparate_impact_ratio_threshold": 0.80,
    "min_group_size_for_audit": 50,
    "fairness_metrics": {
        BiasDimension.REGION: {
            "enabled": True,
            "description": "Ensure no region is disproportionately declined",
            "max_disparity": 0.15,
        },
        BiasDimension.PAYMENT_METHOD: {
            "enabled": True,
            "description": "COD vs card fairness — COD must not be implicitly penalized",
            "max_disparity": 0.10,
        },
        BiasDimension.DEVICE_TYPE: {
            "enabled": False,
            "description": "Device type fairness — reserved for future",
            "max_disparity": 0.15,
        },
    },
    "bias_mitigation": {
        "recalibrate_if_violated": True,
        "fallback_to_human_review": True,
    },
}


ConfidencePolicy = {
    "thresholds": {
        "approve": {"min_confidence": 0.75, "max_risk": 30},
        "review": {"min_confidence": 0.60, "max_risk": 70},
        "decline": {"min_confidence": 0.80, "min_risk": 70},
    },
    "low_confidence_action": "escalate_to_human",
    "uncertainty_tolerance": 0.15,
}


SafetyPolicy = {
    "output_validation": {
        "max_reason_codes": 8,
        "required_fields": ["order_id", "decision", "risk_score", "confidence", "agent_scores", "reason_codes", "latency_ms"],
        "risk_score_range": [0, 100],
        "confidence_range": [0, 1],
        "disallow_negative_values": True,
    },
    "content_moderation": {
        "block_profanity_in_reason_codes": True,
        "block_pii_in_explanations": True,
    },
    "output_guardrails": {
        "approve_must_have_risk_under": 30,
        "decline_must_have_risk_above": 70,
        "review_must_have_risk_between": [30, 70],
    },
}


PiiRules = {
    "patterns": [
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b\d{16}\b",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        r"\b\d{10}\b",
    ],
    "redaction_placeholder": "[REDACTED]",
    "max_exposure_per_response": 0,
}


class ComplianceRegulation(str, Enum):
    GDPR = "gdpr"
    AML = "aml"
    KYC = "kyc"
    PCI_DSS = "pci_dss"
    CCPA = "ccpa"


CompliancePolicy = {
    "enabled_regulations": [
        ComplianceRegulation.GDPR,
        ComplianceRegulation.AML,
        ComplianceRegulation.KYC,
    ],
    "regulations": {
        ComplianceRegulation.GDPR: {
            "require_explanation": True,
            "data_retention_days": 90,
            "right_to_explain": True,
            "prohibit_profiling_without_consent": True,
        },
        ComplianceRegulation.AML: {
            "require_identity_verification_on_threshold": 10000,
            "report_suspicious_activity": True,
            "record_keeping_days": 1825,
        },
        ComplianceRegulation.KYC: {
            "require_customer_verification_for_review": True,
            "minimum_verification_level": "basic",
        },
        ComplianceRegulation.PCI_DSS: {
            "mask_pan_in_logs": True,
            "dont_store_full_pan": True,
        },
    },
    "audit_logging": {
        "log_all_decisions": True,
        "log_all_escalations": True,
        "log_model_versions": True,
        "immutable_audit_trail": True,
    },
}


HumanReviewPolicy = {
    "escalation_triggers": {
        "max_confidence": {"enabled": True, "threshold_below": 0.60},
        "bias_flag": {"enabled": True, "description": "Any bias check failure triggers escalation"},
        "borderline_score": {"enabled": True, "range": [25, 35]},
        "high_value_transaction": {"enabled": True, "threshold_above": 50000},
        "regulation_required": {"enabled": True, "regulations": [ComplianceRegulation.KYC]},
        "low_confidence_high_risk": {"enabled": True, "confidence_below": 0.70, "risk_above": 60},
    },
    "escalation_queue": "human_review_queue",
    "escalation_timeout_hours": 24,
    "auto_approve_if_no_reviewer_in_hours": 48,
    "notify_channels": ["dashboard", "email"],
}
