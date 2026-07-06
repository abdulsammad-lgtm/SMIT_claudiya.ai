# AegisFlow AI — Member 3: Transaction Fraud Engineer

## Hybrid ML + Rules — Technical Specification & Implementation Guide

> **Document Type:** Product Requirements Document + Implementation Spec  
> **Target:** AI Coding Agent  
> **Project:** AegisFlow AI — Production Fraud Detection SaaS  
> **Role:** Member 3 — Transaction Fraud Engineer  
> **Approach:** Hybrid (Hard Rules + XGBoost ML Model)  
> **Stack:** Python 3.11+, FastAPI, XGBoost, SHAP, Redis, PostgreSQL, scikit-learn, joblib  
> **Version:** 2.0 (Production)

-----

## Table of Contents

1. [Why Hybrid? — Defense Key Points](#1-why-hybrid--defense-key-points)
1. [Role Overview](#2-role-overview)
1. [System Context — Where Member 3 Fits](#3-system-context--where-member-3-fits)
1. [Hybrid Architecture — The Two-Layer Design](#4-hybrid-architecture--the-two-layer-design)
1. [Dependencies — What Must Exist Before You Start](#5-dependencies--what-must-exist-before-you-start)
1. [File Structure to Create](#6-file-structure-to-create)
1. [Data Models & Schemas](#7-data-models--schemas)
1. [Redis Schema & Conventions](#8-redis-schema--conventions)
1. [Database Schema](#9-database-schema)
1. [BIN Lookup — API Options & Self-Hosted Strategy](#10-bin-lookup--api-options--self-hosted-strategy)
1. [Freight Forwarder Detection — Three Layers, No API Needed](#11-freight-forwarder-detection--three-layers-no-api-needed)
1. [Fraud Patterns & Static Config](#12-fraud-patterns--static-config)
1. [Layer 1 — Hard Rule Engine](#13-layer-1--hard-rule-engine)
1. [The 25 Features — Complete Reference Guide](#14-the-25-features--complete-reference-guide)
1. [IEEE-CIS Dataset — Initial Training Data Guide](#15-ieee-cis-dataset--initial-training-data-guide)
1. [Chargeback Labeling — How the Model Learns From Real Fraud](#16-chargeback-labeling--how-the-model-learns-from-real-fraud)
1. [Layer 2 — Feature Engineering for ML](#17-layer-2--feature-engineering-for-ml)
1. [Layer 2 — XGBoost Model Training Pipeline](#18-layer-2--xgboost-model-training-pipeline)
1. [Layer 2 — ML Inference (Real-Time)](#19-layer-2--ml-inference-real-time)
1. [Layer 2 — SHAP Explainability](#20-layer-2--shap-explainability)
1. [Score Combination Logic](#21-score-combination-logic)
1. [Model Versioning & Retraining](#22-model-versioning--retraining)
1. [Transaction Agent — Main Orchestration Logic](#23-transaction-agent--main-orchestration-logic)
1. [Output Contract — What You Return to the Orchestrator](#24-output-contract--what-you-return-to-the-orchestrator)
1. [Error Handling Rules](#25-error-handling-rules)
1. [Test Cases](#26-test-cases)
1. [Integration Checklist](#27-integration-checklist)

-----

## 1. Why Hybrid? — Defense Key Points

This section exists so you can defend this architectural decision to clients, investors, or technical reviewers. Every point has a real-world example.

-----

### Point 1 — Fraudsters Reverse-Engineer Rules. They Cannot Reverse-Engineer a Trained Model.

A rule-based system is essentially a public contract. If your rule is “block if a card is used more than 3 times in 10 minutes”, a sophisticated fraud ring will probe your API with test transactions, discover the threshold is 3, and run exactly 2 transactions every 10 minutes forever. This is called **threshold probing** and it is routine among organized fraud operations.

An XGBoost model has no visible threshold. Its decision boundary is a high-dimensional surface learned from thousands of features and their interactions. An attacker cannot probe it without generating labelled training data for you.

**Real example:** Shopify publicly documented in 2022 that after switching from pure rule-based systems to ML-based scoring, adversarial probe-and-evade attacks dropped by over 60% because attackers lost the ability to find the boundaries of the detection system.

-----

### Point 2 — Rules Cannot Capture Feature Interactions. ML Does This Automatically.

Consider three signals individually: (a) prepaid card, (b) VPN-masked IP, (c) account age < 7 days. None of these alone is grounds for blocking a $50 transaction. A rule-based system would let it through.

An XGBoost model trained on historical fraud data learns that this *specific combination* — prepaid card + VPN + new account — on any purchase above $30 in the electronics category has a 94% historical fraud rate. It blocks it. No human wrote that rule. The model discovered it from data.

**Real example:** Research on XGBoost-based e-commerce fraud detection incorporating multi-dimensional feature engineering including behavioral, temporal, and transactional features significantly outperformed traditional classifiers such as Logistic Regression, Random Forest, and SVM in key metrics including recall, F1-score, and AUC across 500,000+ real transactions.

-----

### Point 3 — False Positives Cost You Real Money. ML Reduces Them Significantly.

Every time you block a legitimate customer, you lose that sale, and often the customer permanently. If your rule-based system has a 5% false positive rate and you process $100,000/month in GMV, you are blocking $5,000 worth of legitimate orders every month. At scale, this is catastrophic for a monetised SaaS product.

Hybrid ML-based fraud detection reduced the false positive rate to below 3.5%, minimizing the operational costs associated with manually reviewing false alerts.

The false positive rate benchmark for competitive fintech fraud detection sits below 0.5%. Rule-based fraud detection fails in two predictable ways as it scales: false positive rates rise as transaction volume and user diversity grow, degrading customer experience; and false negative rates rise as fraudsters learn the rule boundaries and route around them.

-----

### Point 4 — The Model Learns From Your Own Chargeback Data. Rules Never Learn.

Every chargeback your platform receives is a labeled training example: “this transaction was fraud.” You feed these labels back into the model and retrain weekly. The model continuously improves on your specific platform’s fraud patterns.

A rule-based system requires a human to read chargeback reports, identify new patterns, write a new rule, test it, and deploy it. This cycle takes days or weeks. By that time, the fraud ring has moved on to a new technique.

Model drift is managed through continuous performance monitoring and periodic retraining on recent labelled data, ensuring the model adapts to evolving fraud tactics, changes in the merchant’s transaction mix, and external factors like new payment methods.

-----

### Point 5 — SHAP Makes ML Explainable. It Is Not a Black Box.

The classic objection to ML in fraud detection is “it’s a black box — I can’t explain to a customer or regulator why a transaction was blocked.” This objection is solved by **SHAP (SHapley Additive Explanations)**.

SHAP generates a per-transaction explanation like: *“This transaction scored 87 because: freight forwarder address contributed +0.41, card velocity contributed +0.23, prepaid card contributed +0.15, AVS no-match contributed +0.08.”* Every decision is fully auditable.

SHAP provides compliance-grade auditability and developer-grade fidelity, executes within a <50ms latency budget, and generates stable, reproducible feature importance logs suitable for regulatory reporting and model governance documentation. Its Shapley value decomposition satisfies the theoretical properties required for defensible audit trails.

This satisfies Member 8’s compliance requirements and gives your customers a transparent, professional product.

-----

### Point 6 — This Is the Actual Industry Standard

This is not an experimental approach. Gradient-boosted decision trees (XGBoost, LightGBM) are the production standard for tabular fraud detection. They handle heterogeneous feature types, produce feature importance scores compatible with SHAP explainability, and run inference in under 5ms on CPU.

PayPal, Stripe, Adyen, Riskified, and Sift all use gradient-boosted trees as the backbone of their fraud scoring with rule-based hard blocks layered on top. You are building to the same standard.

-----

## 2. Role Overview

Member 3 builds the `transaction_agent` — a hybrid fraud scoring agent that combines two layers:

**Layer 1 — Hard Rule Engine:** Deterministic, instant decisions for the most obvious fraud signals. If a hard rule fires, the transaction is blocked immediately and the ML model is never called. These rules cover the cases where you are 100% certain (e.g., known freight forwarder address, extreme card testing velocity).

**Layer 2 — ML Scoring Engine:** An XGBoost classifier that takes 25+ engineered features from the transaction and returns a fraud probability. The rule engine’s computed signals (velocity counts, AVS code, address match status) become features that feed the model alongside raw transaction fields. This layer handles everything rules miss: subtle correlations, feature interactions, evolving patterns.

The two layers combine into a final score (0–100) which is returned to the Orchestrator (Member 2).

-----

## 3. System Context — Where Member 3 Fits

```
[User Places Order]
        |
        v
[Member 6 — Backend API]
  POST /api/v1/transaction/analyze
        |
        v
[Member 2 — Orchestrator]
  asyncio.gather() → fires all agents
        |
   ─────────────────────────────────────────
   |                 |                     |
   v                 v                     v
[Member 3]       [Member 4]           [Member 5]
Transaction      Behavioral           Device &
Agent (YOU)      Agent                IP Agent
  │                  │                     │
  ▼                  │                     │
[Layer 1]            │                     │
Hard Rules           │                     │
  │ (if hard         │                     │
  │  block) ─────────┼─────────────────────┤
  │                  │                     │
  ▼                  │                     │
[Layer 2]            │                     │
Feature Eng.         │                     │
  │                  │                     │
  ▼                  │                     │
[XGBoost             │                     │
 Inference]          │                     │
  │                  │                     │
  ▼                  ▼                     ▼
[Member 2 — Composite Score Engine]
  Weighted combination of all three agent scores
        |
        v
[Member 8 — Guardrail & Compliance]
  Validates score, checks SHAP explanations, applies policy
        |
        v
[Final Decision: APPROVE / STEP-UP / REVIEW / BLOCK]
```

-----

## 4. Hybrid Architecture — The Two-Layer Design

```
                    TRANSACTION PAYLOAD
                           │
                           ▼
              ┌────────────────────────┐
              │   LAYER 1: HARD RULES  │
              │  (deterministic, fast) │
              │                        │
              │  • card_testing?       │
              │  • extreme velocity?   │
              │  • freight_forwarder?  │
              │  • CVV completely      │
              │    missing + AVS N?    │
              └────────────┬───────────┘
                           │
             ┌─────────────┴──────────────┐
             │ Hard block fired?          │
         YES │                            │ NO
             ▼                            ▼
    Return score=100          ┌───────────────────────┐
    flags=[hard_block]        │ LAYER 2: ML SCORING   │
    skip ML                   │                       │
                              │ Feature Engineering   │
                              │  • velocity counts    │
                              │  • AVS encoding       │
                              │  • temporal features  │
                              │  • BIN features       │
                              │  • 25+ total features │
                              │         │             │
                              │         ▼             │
                              │  XGBoost.predict_     │
                              │  proba(features)      │
                              │         │             │
                              │         ▼             │
                              │  fraud_prob → score   │
                              │                       │
                              │  SHAP Explanation     │
                              │  (for audit trail)    │
                              └──────────┬────────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │ FINAL SCORE OUTPUT  │
                              │ score: int (0-100)  │
                              │ flags: list[str]    │
                              │ shap_explanation    │
                              │ check_details       │
                              └─────────────────────┘
```

**Why this exact split:**

- Hard rules handle the ~5% of transactions that are unambiguously fraud. These need zero latency and 100% explainability.
- ML handles the remaining 95% with nuance. Most of these are legitimate; ML catches the ones that look legitimate but aren’t.
- Fraudsters can probe the hard rule thresholds but the hard rules only cover what’s already 100% certain — there’s nothing useful to gain from knowing these boundaries.
- The ML model weights are not visible and retrain weekly — nothing to probe.

-----

## 5. Dependencies — What Must Exist Before You Start

### From Member 6 (Backend API Engineer)

|Dependency                       |Why You Need It                                  |What to Confirm       |
|---------------------------------|-------------------------------------------------|----------------------|
|Redis (running)                  |Velocity checks & feature computation            |`REDIS_URL` env var   |
|PostgreSQL (running)             |Historical data, chargeback labels, training data|`DATABASE_URL` env var|
|`transactions` table             |Training data + velocity fallback                |Schema in Section 9   |
|`chargebacks` table              |Fraud labels for training                        |Schema in Section 9   |
|`fraud_labels` table             |Ground truth for model retraining                |Schema in Section 9   |
|`users` table                    |Account age, trust tier features                 |Schema in Section 9   |
|`init_redis()` called at startup |Before first request                             |In `main.py`          |
|`init_db(pool)` called at startup|asyncpg pool injected                            |In `main.py`          |

### From Member 5 (Device Security Engineer)

|Field Name  |Type  |Why You Need It                     |
|------------|------|------------------------------------|
|`ip_address`|`str` |Velocity checks per IP, BIN mismatch|
|`ip_country`|`str` |BIN vs geo mismatch feature         |
|`is_vpn`    |`bool`|Reduces geo mismatch feature weight |
|`is_proxy`  |`bool`|Used as direct ML feature           |


> **Critical:** Agree on these exact field names with Member 5 before writing any code.

### From Member 2 (Orchestrator Engineer)

|Dependency               |Detail                                         |
|-------------------------|-----------------------------------------------|
|Input payload contract   |Exact field names in Section 7.1               |
|Output contract          |Exact return shape in Section 19               |
|Entry point function name|`analyze(payload: TransactionPayload)` — async |
|Latency budget           |Your agent must complete within **200ms** total|

### ML Model File (you generate this yourself)

|File                          |How It’s Created                                                      |
|------------------------------|----------------------------------------------------------------------|
|`models/xgboost_fraud_v1.pkl` |Run `ml/model_trainer.py` offline on historical data before deployment|
|`models/model_metadata.json`  |Auto-generated by training script                                     |
|`models/shap_explainer_v1.pkl`|Auto-generated by training script                                     |


> The model file must exist on disk before the agent starts. If it doesn’t exist, the agent falls back to rule-only mode (see Section 20 error handling).

-----

## 6. File Structure to Create

```
aegisflow-ai/
├── agents/
│   └── transaction_agent.py          ← MAIN: agent entry point, combines both layers
│
├── tools/
│   ├── velocity_checker.py           ← Layer 1 + feature: velocity check logic (Redis)
│   └── fraud_patterns.py             ← Static configs, thresholds, lookup tables
│
├── ml/
│   ├── feature_engineering.py        ← Computes the 25 ML features from payload
│   ├── model_trainer.py              ← OFFLINE: trains XGBoost on historical data
│   ├── model_inference.py            ← REAL-TIME: loads model, runs inference
│   └── shap_explainer.py             ← Generates per-transaction SHAP explanations
│
├── services/
│   └── bin_lookup.py                 ← BIN database query logic
│
├── models/                           ← Generated files — not hand-written
│   ├── xgboost_fraud_v1.pkl          ← Trained model (generated by model_trainer.py)
│   ├── shap_explainer_v1.pkl         ← SHAP TreeExplainer (generated by trainer)
│   ├── feature_scaler_v1.pkl         ← StandardScaler (generated by trainer)
│   └── model_metadata.json           ← Version, date, metrics (generated by trainer)
│
└── tests/
    ├── test_transaction_agent.py     ← End-to-end agent tests
    ├── test_feature_engineering.py   ← Unit tests for feature computation
    └── test_model_inference.py       ← Unit tests for ML inference
```

-----

## 7. Data Models & Schemas

### 7.1 — Input Payload (What Member 2 sends to your agent)

```python
# In agents/transaction_agent.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TransactionPayload(BaseModel):
    # ── Core Transaction Fields ──────────────────────────────────
    transaction_id: str
    user_id: str
    timestamp: datetime              # UTC

    # ── Card Fields ──────────────────────────────────────────────
    card_bin: str                    # First 6 digits
    card_last4: str                  # Last 4 digits
    amount: float                    # In base currency (USD)
    currency: str                    # ISO 4217: "USD", "PKR", etc.
    cvv_provided: bool
    avs_result: str                  # "Y", "N", "Z", "A", "U"

    # ── Address Fields ───────────────────────────────────────────
    billing_address: str
    billing_country: str             # ISO 3166-1 alpha-2: "PK", "US"
    billing_zip: str
    shipping_address: str
    shipping_country: str
    shipping_zip: str

    # ── Merchant Fields ──────────────────────────────────────────
    merchant_id: str
    merchant_category: str           # Must match key in MERCHANT_RISK_MULTIPLIERS

    # ── Device/IP Fields (enriched by Member 5) ──────────────────
    ip_address: str
    ip_country: str
    is_vpn: bool
    is_proxy: bool
```

### 7.2 — Output Payload (What your agent returns to Member 2)

```python
class SHAPExplanation(BaseModel):
    top_features: list[dict]         # Top 5 features by contribution
    # Each dict: {"feature": "card_velocity_count", "contribution": 0.23, "value": 5}

class TransactionAgentResult(BaseModel):
    agent: str                       # Always "transaction_agent"
    score: int                       # Final fraud sub-score, 0–100
    flags: list[str]                 # Triggered flag keys (see VALID_FLAGS)
    hard_blocked: bool               # True if Layer 1 triggered an immediate block
    ml_fraud_probability: float      # Raw XGBoost output 0.0–1.0 (0.0 if hard blocked)
    shap_explanation: Optional[SHAPExplanation]  # None if hard blocked
    check_details: dict              # Full per-check audit trail
    error: Optional[str]             # None if successful
```

### 7.3 — Valid Flag Keys

```python
VALID_FLAGS = [
    # Layer 1 — Hard Rule Flags (immediate block)
    "hard_block_card_testing",
    "hard_block_extreme_velocity",
    "hard_block_freight_forwarder",
    "hard_block_cvv_and_avs_fail",

    # Layer 2 — ML Feature Flags (soft signals, contribute to score)
    "card_velocity_elevated",
    "ip_velocity_elevated",
    "user_velocity_elevated",
    "bin_country_mismatch",
    "bin_prepaid_high_value",
    "bin_lookup_failed",
    "avs_no_match",
    "avs_partial_match",
    "cvv_missing_or_failed",
    "address_country_mismatch",
    "address_city_mismatch",
    "high_risk_merchant_category",
    "chargeback_history_detected",
    "high_return_rate",
    "new_account_high_value",
    "vpn_detected",
    "amount_spike_detected",

    # System Flags
    "ml_model_unavailable",         # Model file missing — fell back to rules only
    "agent_error",                  # Unexpected failure
]
```

-----

## 8. Redis Schema & Conventions

Velocity state and recent transaction windows are stored in Redis sorted sets.

|Key Pattern             |Example                    |Window  |Purpose                                 |
|------------------------|---------------------------|--------|----------------------------------------|
|`vel:card:{bin}{last4}` |`vel:card:4111114242`      |10 min  |Card attempt velocity                   |
|`vel:ip:{ip}`           |`vel:ip:103.45.67.89`      |5 min   |IP transaction velocity                 |
|`vel:user:{user_id}`    |`vel:user:usr_4421`        |1 hour  |User order velocity                     |
|`vel:ip:micro:{ip}`     |`vel:ip:micro:103.45.67.89`|2 min   |Micro-transaction tracking              |
|`feat:card:{bin}{last4}`|`feat:card:4111114242`     |24 hours|Last 24h amount list for spike detection|

**Implementation pattern for all velocity keys (use Redis sorted sets):**

```python
def _record_and_count(redis_client, key: str, member: str, window_seconds: int) -> int:
    now = time.time()
    pipe = redis_client.pipeline()
    pipe.zadd(key, {member: now})
    pipe.zremrangebyscore(key, 0, now - window_seconds)
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 60)
    results = pipe.execute()
    return results[2]  # zcard result
```

-----

## 9. Database Schema

Tables you read from (Member 6 creates them). Confirm these columns exist.

```sql
-- transactions: all historical transactions
-- Columns used: transaction_id, user_id, card_bin, card_last4,
--               amount, status, created_at
SELECT amount FROM transactions
WHERE user_id = $1 AND created_at > NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;

-- chargebacks: all filed chargebacks
-- Columns used: user_id, created_at, reason, status
SELECT COUNT(*) FROM chargebacks
WHERE user_id = $1 AND created_at > NOW() - INTERVAL '90 days';

-- fraud_labels: ground truth for model retraining
-- *** THIS TABLE MUST BE CREATED. Confirm with Member 6. ***
CREATE TABLE fraud_labels (
    transaction_id  VARCHAR PRIMARY KEY,
    user_id         VARCHAR NOT NULL,
    label           SMALLINT NOT NULL,   -- 1 = confirmed fraud, 0 = confirmed legit
    label_source    VARCHAR,             -- 'chargeback', 'manual_review', 'model_feedback'
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- users: user account data
-- Columns used: user_id, created_at, trust_tier, total_orders, return_count
SELECT created_at, trust_tier, total_orders, return_count
FROM users WHERE user_id = $1;
```

-----

## 10. BIN Lookup — API Options & Self-Hosted Strategy

### What BIN Data Is and Why You Need It

BIN stands for Bank Identification Number. It is the first 6–8 digits of any card number. Every BIN is registered globally to a specific bank, in a specific country, for a specific card type (credit, debit, prepaid, gift, virtual). This data does not live anywhere in the transaction payload — the merchant only sends you the BIN digits, not what they mean. You have to look them up.

From a BIN lookup you get three things that directly become ML features: the issuing country (for `bin_country_match`), the card type (for `is_prepaid_card`), and the issuing bank name (used contextually). Without a BIN lookup, three of your 25 features are blind.

### Option 1 — Call an External BIN API in Real-Time

This is the approach for early development and low-volume production.

**BINSearchLookup** — This is the recommended starting point. Free tier gives 500 requests per month with no credit card required. It covers 1.4 million BIN ranges across 200+ countries and returns card type (credit, debit, prepaid, gift, virtual), issuing bank, and issuing country. It is GDPR and PCI DSS compliant. Upgrade to paid tiers as transaction volume grows.

**binlist.net** — Completely free, no API key needed. Returns country, bank, card type, and card brand. Rate-limited at roughly 10 requests per second and has no SLA or uptime guarantee. Acceptable for development testing only. Do not use in production — if binlist.net goes down, your BIN features go blind on every transaction.

**Neutrino API** — Paid service, more reliable, richer data including fraud risk scores per BIN range. Worth evaluating when you cross 10,000 transactions per day.

**The critical rule for any external BIN API:** Set a hard timeout of 2 seconds. If the API does not respond in 2 seconds, return neutral BIN values (`bin_country_match = 0.5`, `is_prepaid = 0.0`) and add a `bin_lookup_failed` flag. Never let a slow external API delay your 130ms latency budget. The 2-second timeout is your circuit breaker.

### Option 2 — Self-Hosted BIN Database (Recommended for Production)

At production scale, calling an external API on every transaction introduces a dependency that can fail, rate-limit you, or add latency. The industry-standard approach is to download a full BIN database as a flat file and host it in your own PostgreSQL instance.

BIN databases are available as downloadable CSV or SQLite files. You load the entire database into a `bin_database` table in PostgreSQL, create an index on the BIN prefix column, and query it locally. A local database query takes under 1 millisecond — far better than an HTTP call.

The tradeoff is staleness — new BIN ranges are issued as new cards are created. You refresh the database monthly by re-downloading and re-importing the file. For fraud detection purposes, a monthly refresh is more than sufficient. BIN ranges that are not in your database return neutral values, which is safe.

**The migration path:** Start with the BINSearchLookup free API during development. Before your first real production launch, download a full BIN database snapshot, import it into PostgreSQL, and switch `bin_lookup.py` from an HTTP call to a DB query. The rest of your code does not change — only the implementation inside `bin_lookup.py` changes.

### Additional Table Required in PostgreSQL

When you migrate to self-hosted, Member 6 needs to create this table:

```sql
CREATE TABLE bin_database (
    bin_prefix      VARCHAR(8) PRIMARY KEY,   -- first 6-8 digits
    card_type       VARCHAR(50),              -- credit, debit, prepaid, gift, virtual
    card_brand      VARCHAR(50),              -- visa, mastercard, amex, discover
    issuing_bank    VARCHAR(255),
    issuing_country VARCHAR(2),               -- ISO alpha-2 country code
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_bin_prefix ON bin_database(bin_prefix);
```

Query pattern: match the longest prefix of the card number against the table. Start with 8 digits, fall back to 6 if no match found.

### Fallback Values When BIN Lookup Fails

| Situation | `bin_country_match` | `is_prepaid_card` | Flag Added |
|---|---|---|---|
| Successful lookup, country matches IP | 1.0 | 0.0 or 1.0 from data | None |
| Successful lookup, country does not match IP | 0.0 | 0.0 or 1.0 from data | `bin_country_mismatch` |
| Successful lookup, IP is VPN (uncertain) | 0.5 | 0.0 or 1.0 from data | None |
| BIN not found in database | 0.5 | 0.0 | None |
| API timeout or error | 0.5 | 0.0 | `bin_lookup_failed` |

The 0.5 value for uncertain cases is intentional. XGBoost will learn that 0.5 means "unknown" and will weight this feature less heavily when it is 0.5 versus when it is a definitive 0 or 1.

---

## 11. Freight Forwarder Detection — Three Layers, No API Needed

### What a Freight Forwarder Is and Why It Matters

A freight forwarder (also called a reshipping service) is a physical warehouse, usually in the US or UK, that accepts deliveries and then re-ships them to another international address on behalf of the recipient. Legitimate freight forwarders exist to help people in countries where international shipping is not available. Fraudsters abuse them to obscure the true destination of stolen goods.

The fraud pattern looks like this: a fraudster in Nigeria steals a UK card and wants to buy $500 of electronics. If they ship to Nigeria, the merchant's geo-mismatch check catches it immediately. Instead, they ship to a freight forwarder in Miami. The Miami address looks legitimate. The warehouse receives the package and re-ships it to Nigeria. The merchant has no idea.

The key insight is that freight forwarder detection does not need a real-time API. You can cover the vast majority of cases with three layers of static detection, each of which is either a set membership test or a string match — operations that take nanoseconds.

### Layer 1 — Keyword Matching on the Address String

This is already in your `fraud_patterns.py`. You check whether the shipping address string contains words that identify a freight forwarder or commercial mail receiving agency. These businesses describe themselves consistently in their addresses and business names.

Keywords to match against: `freight`, `forwarder`, `forwarding`, `reshipping`, `pmb` (personal mailbox), `mailbox`, `mailboxes etc`, `the ups store`, `ups store`, `pak mail`, `mailstop`, `mail stop`, `suite` combined with a suite number pattern that suggests a commercial mailbox rather than an apartment.

This catches a large proportion of cases because freight forwarder businesses use these terms in their registered addresses, and fraudsters copy the address exactly from the freight forwarder's website.

### Layer 2 — Static ZIP Code List

Service Objects and other fraud prevention providers publish free lists of known freight forwarder addresses and ZIP codes. These are concentrated in specific areas:

Miami, FL (ZIP codes 33166, 33126, 33172) is the single largest freight forwarding hub in the US, specifically because of proximity to Latin America. New York (10001, 11101) is the second largest hub. Los Angeles (90220), Houston (77032), and Delaware (19720) are also major hubs. Delaware specifically because of its business registration laws — many reshipping companies incorporate there.

You maintain this as a Python `set` in `fraud_patterns.py`. A set membership check (`zip_code in KNOWN_FREIGHT_FORWARDER_ZIPS`) is an O(1) operation. You check the shipping ZIP against this set on every transaction.

Update this list quarterly by reviewing Service Objects' published data and any new freight forwarder ZIPs you discovered through your own chargebacks.

### Layer 3 — Your Own Chargeback-Derived Hotlist

This is the most powerful layer over time. Every time a transaction gets charged back and you trace it to a shipping address that was not in your static list, you add that address to your own `freight_forwarder_addresses` table in PostgreSQL. Your system learns from its own fraud experience.

Member 6 needs to create this table:

```sql
CREATE TABLE freight_forwarder_addresses (
    address_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipping_zip    VARCHAR(10),
    address_snippet VARCHAR(255),    -- partial address or keyword that identifies it
    source          VARCHAR(50),     -- 'chargeback', 'manual_review', 'static_list'
    confirmed_fraud_count INTEGER DEFAULT 1,
    added_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_ff_zip ON freight_forwarder_addresses(shipping_zip);
```

Your `check_freight_forwarder_hard_block()` function in `velocity_checker.py` queries this table alongside the static list. When a chargeback comes in and a fraud analyst confirms the shipping address was a freight forwarder, they add it to this table via the dashboard. Over 6 months of operation, this hotlist becomes the most accurate part of your detection — it reflects your actual fraud patterns, not a generic industry list.

### Hard Block vs. ML Feature

There is an important distinction between how freight forwarder detection is used in Layer 1 and Layer 2:

In **Layer 1 (hard block)**, a definitive freight forwarder match — ZIP code in your known list OR specific business keywords in the address — results in an immediate score=100 block. The ML model is never called.

In **Layer 2 (ML feature)**, the `is_freight_forwarder` feature captures near-matches that didn't trigger the hard block — for example, an address that contains the word "suite" without a business keyword, or a ZIP that is close to but not in your known list. The ML model weighs this partial signal alongside everything else. This gives you a graduated response: definitive matches hard block, ambiguous matches get scored by ML.

### No API Required

To summarize: freight forwarder detection is entirely self-contained. You need no external service, no third-party API, no runtime HTTP calls. The full detection stack is keyword matching (nanoseconds), ZIP set lookup (nanoseconds), and a PostgreSQL query on your own hotlist (under 1ms). All of this fits comfortably within your 130ms latency budget.

---

## 12. Fraud Patterns & Static Config

**File:** `tools/fraud_patterns.py`

```python
# tools/fraud_patterns.py

# ─────────────────────────────────────────────────────────────────
# LAYER 1 — HARD BLOCK THRESHOLDS
# These trigger an immediate score=100 block. ML is not called.
# ─────────────────────────────────────────────────────────────────

HARD_BLOCK_RULES = {
    "card_testing": {
        # Micro-transaction burst + large spike from same IP within 2 minutes
        "micro_amount": 1.00,
        "micro_count": 2,
        "window_seconds": 120,
        "spike_ratio": 50,
    },
    "extreme_velocity": {
        # Same card used more than this many times in any 5-minute window
        "card_max_attempts": 8,
        "window_seconds": 300,
    },
    "cvv_and_avs_combined": {
        # Both CVV missing AND AVS=N is near-definitive stolen card
        # This hard blocks regardless of other signals
        "requires_cvv_missing": True,
        "requires_avs_code": "N",
    },
}

# ─────────────────────────────────────────────────────────────────
# LAYER 2 — SOFT RULE THRESHOLDS (become ML features)
# These do NOT trigger hard blocks. They are computed and passed
# as numeric features to XGBoost.
# ─────────────────────────────────────────────────────────────────

SOFT_VELOCITY_THRESHOLDS = {
    "card": {"max_attempts": 3, "window_seconds": 600},
    "ip": {"max_attempts": 5, "window_seconds": 300},
    "user": {"max_attempts": 4, "window_seconds": 3600},
}

AVS_SCORE_MAP = {
    "Y": 0,    # Full match
    "A": 1,    # Street only
    "Z": 2,    # ZIP only
    "N": 3,    # No match
    "U": 1,    # Unavailable
    "E": 1,    # Not eligible
    "S": 1,    # Service unavailable
}

MERCHANT_RISK_MULTIPLIERS = {
    "gift_cards":   1.8,
    "crypto":       1.7,
    "electronics":  1.4,
    "jewelry":      1.3,
    "luxury_goods": 1.3,
    "gaming":       1.2,
    "clothing":     1.0,
    "home_goods":   0.9,
    "books":        0.7,
    "groceries":    0.6,
    "utilities":    0.4,
    "default":      1.0,
}

# Flag if category multiplier is at or above this
HIGH_RISK_MERCHANT_THRESHOLD = 1.3

KNOWN_FREIGHT_FORWARDER_ZIPS = {
    "33166", "33126", "33172",   # Miami, FL
    "10001", "11101",             # New York
    "90220",                      # Los Angeles
    "77032",                      # Houston
    "19720",                      # Delaware
}

KNOWN_FREIGHT_FORWARDER_KEYWORDS = [
    "freight", "forwarder", "forwarding", "reshipping",
    "pmb", "mailbox", "mailboxes etc", "ups store",
    "pak mail", "mailstop",
]

BIN_CONFIG = {
    "vpn_geo_weight_multiplier": 0.5,
    "prepaid_high_value_threshold": 100.0,
}

CHARGEBACK_CONFIG = {
    "lookback_days": 90,
    "high_return_rate_threshold": 0.40,
}

NEW_ACCOUNT_CONFIG = {
    "age_days_threshold": 7,
    "high_value_threshold": 200.0,
}

# ─────────────────────────────────────────────────────────────────
# ML FEATURE CONFIG — names and order must match model training
# ─────────────────────────────────────────────────────────────────

ML_FEATURE_NAMES = [
    "amount",
    "amount_log",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "card_velocity_count",
    "ip_velocity_count",
    "user_velocity_count",
    "avs_code_encoded",
    "cvv_missing",
    "billing_shipping_country_match",
    "billing_shipping_zip_match",
    "is_freight_forwarder",
    "bin_country_match",
    "is_vpn",
    "is_proxy",
    "is_prepaid_card",
    "merchant_risk_multiplier",
    "account_age_days",
    "chargeback_count_90d",
    "return_rate",
    "total_orders",
    "is_new_account",
    "amount_vs_user_avg_ratio",
    "is_micro_transaction",
]
```

-----

## 11. Layer 1 — Hard Rule Engine

**File:** `tools/velocity_checker.py` + inline in `agents/transaction_agent.py`

Layer 1 runs first. If any hard rule fires, your agent returns `score=100` immediately and never calls the ML model. This gives your system sub-millisecond response on the most obvious fraud.

```python
# tools/velocity_checker.py

import time
import redis as redis_lib
from tools.fraud_patterns import HARD_BLOCK_RULES, SOFT_VELOCITY_THRESHOLDS

redis_client = None

def init_redis(redis_url: str):
    global redis_client
    redis_client = redis_lib.Redis.from_url(redis_url, decode_responses=True)


def _record_and_count(key: str, member: str, window_seconds: int) -> int:
    now = time.time()
    pipe = redis_client.pipeline()
    pipe.zadd(key, {member: now})
    pipe.zremrangebyscore(key, 0, now - window_seconds)
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 60)
    results = pipe.execute()
    return results[2]


# ── Hard block: extreme card velocity ────────────────────────────────────────

def check_extreme_velocity(card_bin: str, card_last4: str, txn_id: str) -> bool:
    """
    Returns True (hard block) if this card has been attempted more than
    the extreme threshold times in a 5-minute window.
    This is distinct from soft velocity — soft is 3 in 10 min,
    hard is 8 in 5 min. By the time someone hits the hard threshold,
    it's unambiguously an automated attack.
    """
    cfg = HARD_BLOCK_RULES["extreme_velocity"]
    key = f"vel:card:{card_bin}{card_last4}"
    count = _record_and_count(key, txn_id, cfg["window_seconds"])
    return count > cfg["card_max_attempts"]


# ── Hard block: card testing pattern ─────────────────────────────────────────

def check_card_testing_hard_block(
    ip_address: str, txn_id: str, current_amount: float
) -> bool:
    """
    Returns True (hard block) if this is a large charge following a burst
    of micro-transactions from the same IP within 2 minutes.
    Card testing is the clearest fraud signal that exists —
    no legitimate user places $0.99 charges followed by a $500 charge
    from the same IP within 120 seconds.
    """
    cfg = HARD_BLOCK_RULES["card_testing"]
    micro_key = f"vel:ip:micro:{ip_address}"
    now = time.time()

    is_micro = current_amount <= cfg["micro_amount"]
    if is_micro:
        pipe = redis_client.pipeline()
        pipe.zadd(micro_key, {txn_id: now})
        pipe.expire(micro_key, cfg["window_seconds"] + 30)
        pipe.execute()
        return False  # The micro-transaction itself is not blocked here

    # Current transaction is large — check for prior micro burst
    micro_count = redis_client.zcount(
        micro_key, now - cfg["window_seconds"], now
    )
    spike_ratio = current_amount / cfg["micro_amount"]
    return (micro_count >= cfg["micro_count"] and
            spike_ratio >= cfg["spike_ratio"])


# ── Hard block: freight forwarder address ────────────────────────────────────

def check_freight_forwarder_hard_block(
    shipping_zip: str, shipping_address: str
) -> bool:
    """
    Returns True (hard block) if the shipping address matches a known
    freight forwarder ZIP or contains freight forwarder keywords.
    """
    from tools.fraud_patterns import (
        KNOWN_FREIGHT_FORWARDER_ZIPS,
        KNOWN_FREIGHT_FORWARDER_KEYWORDS,
    )
    addr_lower = shipping_address.lower()
    return (
        shipping_zip in KNOWN_FREIGHT_FORWARDER_ZIPS
        or any(kw in addr_lower for kw in KNOWN_FREIGHT_FORWARDER_KEYWORDS)
    )


# ── Hard block: CVV + AVS combined failure ───────────────────────────────────

def check_cvv_avs_combined_hard_block(cvv_provided: bool, avs_result: str) -> bool:
    """
    Returns True (hard block) if both CVV is missing AND AVS returned N.
    This combination means: the person doesn't have the physical card
    (no CVV) AND the billing address is completely wrong.
    This is the signature of a card number bought off the dark web
    where only the card number and expiry were in the dump.
    """
    return (not cvv_provided and avs_result.upper() == "N")


# ── Soft velocity: returns count values (used as ML features) ────────────────

def get_velocity_features(
    card_bin: str, card_last4: str, ip_address: str, user_id: str, txn_id: str
) -> dict:
    """
    Computes soft velocity counts for all three dimensions.
    These are NOT hard blocks — they are numeric features passed to XGBoost.
    The ML model decides how much weight to give each count.
    """
    cfg = SOFT_VELOCITY_THRESHOLDS
    return {
        "card_velocity_count": _record_and_count(
            f"vel:card:{card_bin}{card_last4}", txn_id, cfg["card"]["window_seconds"]
        ),
        "ip_velocity_count": _record_and_count(
            f"vel:ip:{ip_address}", txn_id, cfg["ip"]["window_seconds"]
        ),
        "user_velocity_count": _record_and_count(
            f"vel:user:{user_id}", txn_id, cfg["user"]["window_seconds"]
        ),
    }
```

-----

## 14. The 25 Features — Complete Reference Guide

This section documents every single feature in the ML feature vector. For each feature you will find: what it represents, why it catches fraud, what values it typically takes, and exactly where it comes from. This is the canonical reference — any discrepancy between this section and the actual `compute_features()` implementation is a bug.

The feature vector must always be produced in the exact order listed here. XGBoost does not know feature names — it only knows positions. Feature 0 is always `amount`, feature 1 is always `amount_log`, and so on. Changing the order without retraining the model produces silently wrong predictions.

---

### Group 1 — Amount Features

**Feature 0: `amount`**
The raw transaction amount in the merchant's base currency (USD). This is the most obvious input but weaker as a standalone signal than people expect — a $500 transaction is not inherently suspicious. Its power comes from context, specifically when combined with `amount_vs_user_avg_ratio` and merchant category. Typical values: $5 to $2000 for normal e-commerce. Extreme values above $5000 should be looked at carefully.

**Feature 1: `amount_log`**
This is `log(1 + amount)`. Transaction amounts follow a heavily right-skewed distribution — the vast majority of real transactions are small ($10–$100) and a tiny fraction are very large. If you feed raw dollar amounts to XGBoost, a $5000 transaction dominates the model's attention purely by its magnitude, even if it is perfectly legitimate. The log transformation compresses the range so that the difference between $10 and $100 is weighted similarly to the difference between $1000 and $10000. The `+1` ensures $0.00 transactions (which exist in card testing scenarios) do not produce negative infinity. This is standard practice for any financial ML model.

---

### Group 2 — Temporal Features

**Feature 2: `hour_of_day`**
The UTC hour (0–23) when the transaction was submitted. Fraud has a distinct temporal signature. Real purchases cluster during waking hours — roughly 8am to 10pm local time. Fraud bots, especially those running automated card testing, often operate in the early morning hours (1am–5am) when monitoring is lighter and human review queues are empty. The model learns these time-of-day fraud patterns from historical data without you needing to define them manually.

**Feature 3: `day_of_week`**
Integer 0 (Monday) through 6 (Sunday). Different fraud types peak on different days. Gift card fraud spikes on weekends when legitimate high-volume gift card purchases also spike — fraudsters exploit this noise to hide. Account takeover fraud peaks mid-week when cardholders are less likely to check their statements. The model learns merchant-specific day-of-week patterns.

**Feature 4: `is_weekend`**
Binary 0 or 1 derived from `day_of_week` — 1 if Saturday or Sunday, 0 otherwise. This is technically redundant with `day_of_week` but it makes the weekend pattern explicit rather than requiring the model to discover that days 5 and 6 are a meaningful grouping. Both features are kept because they capture different aspects: `day_of_week` captures the full weekly cycle, `is_weekend` makes the weekday/weekend split immediate.

---

### Group 3 — Velocity Features

These three features come from Redis sorted set queries performed in the velocity checker before feature engineering runs. They are numeric counts, not binary flags.

**Feature 5: `card_velocity_count`**
How many times this specific card (identified by BIN + last4) has been used in the last 10 minutes, including the current transaction. A value of 1 means this is the only recent use — normal. A value of 3 or above triggers a soft flag. A value of 8 or above triggers a hard block in Layer 1. Between 3 and 8, the ML model weighs this count alongside other signals. The model learns that card_velocity_count=4 on a gift card purchase in the middle of the night is far more suspicious than card_velocity_count=4 on a grocery purchase at noon.

**Feature 6: `ip_velocity_count`**
How many transactions have originated from this IP address in the last 5 minutes. A single home or mobile IP should generate at most 1–2 transactions in 5 minutes. Anything above 4 indicates a bot or script running multiple card attempts from one machine. This is the primary card farm detection signal. A value of 20+ means an automated attack is actively running from this IP.

**Feature 7: `user_velocity_count`**
How many orders this user account has placed in the last hour. Distinguishes an unusually active legitimate user from an account being abused. Power users occasionally place 2–3 orders per hour. More than 4 orders per hour from the same account, especially across different payment methods, indicates account abuse.

---

### Group 4 — Card Verification Features

**Feature 8: `avs_code_encoded`**
The AVS (Address Verification Service) result encoded as an ordinal number. When you submit a payment, the card's issuing bank compares the billing address you sent against the address they have on file for the cardholder. They return a one-letter code. You encode these ordinally because there is a natural risk ordering:

- Y (full match — street and ZIP both correct) → encoded as 0. No added risk.
- A (street matches, ZIP doesn't) → encoded as 1. Slight risk.
- Z (ZIP matches, street doesn't) → encoded as 2. Moderate risk.
- N (neither matches) → encoded as 3. High risk — someone used the wrong billing address entirely.
- U (bank doesn't support AVS) → encoded as 1. Slight risk.

Ordinal encoding is used here rather than one-hot encoding because the risk genuinely increases from Y to N. One-hot encoding would hide this ordering from the model.

**Feature 9: `cvv_missing`**
Binary 0 or 1. If the CVV (the 3-digit code on the back of the card) was not provided, this is 1. CVV is never stored after a transaction — regulations from PCI DSS prohibit it. This means if someone has the card number but not the CVV, they obtained the card number from a data breach where CVV was not captured (which is common — many card dump files contain only card number and expiry). A missing CVV combined with an AVS mismatch is the signature of a card used without the physical card present.

---

### Group 5 — Address Features

**Feature 10: `billing_shipping_country_match`**
Binary 1 if billing country equals shipping country, 0 if they differ. Most people ship to themselves — billing and shipping country should match. International gifting exists, but it is far less common than domestic purchases. Cross-country mismatches, especially between low-fraud countries (billing) and high-fraud corridors (shipping), are meaningful signals.

**Feature 11: `billing_shipping_zip_match`**
Binary 1 if billing ZIP equals shipping ZIP, 0 if different. This is a softer signal than country mismatch — many legitimate users ship to their office (different ZIP than home billing address) or buy gifts for friends. Alone it adds little. Combined with other signals it contributes to the overall risk picture.

**Feature 12: `is_freight_forwarder`**
Binary 1 if the shipping address matched a freight forwarder pattern (see Section 11 for the full three-layer detection logic), 0 otherwise. Note that in Layer 1, a definitive freight forwarder match triggers a hard block and this feature never reaches the ML model. In Layer 2, this feature captures near-matches — addresses that look like freight forwarders but didn't meet the hard block threshold (for example, a "Suite 400" address without any keywords). The model learns to treat even partial freight forwarder signals as elevated risk when combined with other signals.

---

### Group 6 — BIN and Device Features

**Feature 13: `bin_country_match`**
Continuous value: 1.0 if the BIN issuing country matches the IP country, 0.0 if they don't match, and 0.5 if the IP is a VPN (making the IP country unreliable). Three-valued rather than binary because the VPN case introduces genuine uncertainty — you don't know if the real location matches or not. XGBoost learns to treat 0.5 (uncertain) differently from a definitive 0 (confirmed mismatch). This feature is computed from two data sources: the BIN lookup result (Section 10) and Member 5's IP country enrichment.

**Feature 14: `is_vpn`**
Binary 0 or 1 from Member 5's device agent. VPN detection is done by Member 5 who checks the IP's ASN (Autonomous System Number) against a list of known VPN providers and datacenters. A VPN alone is not a block signal — many legitimate users use VPNs for privacy. But combined with other signals (new account, prepaid card, AVS mismatch, gift card purchase), VPN usage contributes meaningfully to risk score.

**Feature 15: `is_proxy`**
Binary 0 or 1 from Member 5. Proxies and Tor exit nodes are higher-risk than VPN because they are used more specifically to hide identity in transactional contexts. A Tor exit node in a checkout is a very strong signal because Tor's primary use case is anonymity, not privacy — and there is rarely a legitimate reason to complete an e-commerce purchase through Tor.

**Feature 16: `is_prepaid_card`**
Binary 0 or 1 from the BIN lookup. Prepaid cards are anonymous — they are purchased with cash, not linked to a bank account, and carry no verified identity. They are the preferred payment method for fraudsters because they can be acquired without identification and discarded after use. Prepaid flag on any purchase above $100 is a meaningful elevated signal.

---

### Group 7 — Merchant Feature

**Feature 17: `merchant_risk_multiplier`**
The numeric risk multiplier for the merchant's product category, drawn from `MERCHANT_RISK_MULTIPLIERS` in `fraud_patterns.py`. Gift cards get 1.8, electronics 1.4, clothing 1.0, groceries 0.6, utilities 0.4. Rather than one-hot encoding all categories (which adds many columns), you encode the category as its risk multiplier — a single continuous number that carries risk-level information. This allows the model to see that gift_cards and crypto are similar in risk profile while still distinguishing them from clothing and groceries.

---

### Group 8 — User History Features

These five features all come from database queries against the `users` and `chargebacks` tables, run asynchronously during feature engineering.

**Feature 18: `account_age_days`**
The number of days since this user account was created. New accounts placing large orders are one of the most consistent fraud predictors across all e-commerce fraud. Fraudsters create new accounts because they cannot use existing ones (those get locked after previous fraud). An account that is 1 day old placing a $400 electronics order is dramatically different from a 3-year-old account doing the same. This comes from `users.created_at`.

**Feature 19: `chargeback_count_90d`**
How many chargebacks this user has filed in the last 90 days. This is the strongest historical signal in the entire feature set. Chargebacks are the official bank confirmation that a transaction was unauthorized. A user with even 1 chargeback in 90 days is elevated risk. A user with 3 is extremely high risk. This comes from a COUNT query on the `chargebacks` table.

**Feature 20: `return_rate`**
The ratio of returns to total orders — `return_count / total_orders`. High return rates combined with chargebacks suggest friendly fraud: buy the product, receive it, then dispute the charge to get a refund while keeping the item. This feature is only meaningful when `total_orders` is above 3 — a single return out of a single order gives a 100% return rate which is meaningless without volume context. For users with 3 or fewer orders, this feature defaults to 0.0.

**Feature 21: `total_orders`**
The raw lifetime order count for this user account. This provides essential context for interpreting `chargeback_count_90d` and `return_rate`. Two chargebacks in 90 days means something very different for a user with 5 total orders (40% fraud rate) versus a user with 500 total orders (0.4% fraud rate). The model uses this number to contextualize the chargeback and return signals.

**Feature 22: `is_new_account`**
Binary 1 if account age is under 7 days, 0 otherwise. This is derived from `account_age_days` but kept as a separate feature because the "new account" pattern has a sharp cliff rather than a gradual slope — a 6-day-old account is dramatically different from an 8-day-old account in fraud risk terms, but a 30-day-old account vs. a 60-day-old account is not. The binary feature makes this cliff explicit for the model. Both raw age and the binary flag are kept.

---

### Group 9 — Behavioral and Amount Context Features

**Feature 23: `amount_vs_user_avg_ratio`**
The current transaction amount divided by this user's average approved transaction amount over the last 30 days. If a user normally spends $45 per order and this transaction is $900, the ratio is 20 — a dramatic anomaly. If a user normally spends $500 and this transaction is $600, the ratio is 1.2 — completely normal. This feature captures what raw amount cannot: whether this transaction is unusual for this specific person. A new user with no transaction history defaults to 1.0 (neutral).

**Feature 24: `is_micro_transaction`**
Binary 1 if the transaction amount is $1.00 or less, 0 otherwise. This is the card testing signal at the ML layer. Your Layer 1 hard block catches a burst of micro-transactions followed by a large spike from the same IP. But a single micro-transaction on its own does not hard block — it flows to the ML model as this feature. The model learns that micro-transactions, especially combined with new accounts, high IP velocity, or gift card category, are indicative of card testing setup activity.

---

### Feature Vector Assembly — Position Reference

```
Position  Feature Name                   Source
────────  ────────────────────────────   ──────────────────────────────────────
0         amount                         payload.amount
1         amount_log                     log(1 + payload.amount)
2         hour_of_day                    payload.timestamp.hour
3         day_of_week                    payload.timestamp.weekday()
4         is_weekend                     1 if weekday >= 5 else 0
5         card_velocity_count            Redis sorted set count (10-min window)
6         ip_velocity_count              Redis sorted set count (5-min window)
7         user_velocity_count            Redis sorted set count (60-min window)
8         avs_code_encoded               AVS_SCORE_MAP[payload.avs_result]
9         cvv_missing                    0 if payload.cvv_provided else 1
10        billing_shipping_country_match 1 if billing_country == shipping_country
11        billing_shipping_zip_match     1 if billing_zip == shipping_zip
12        is_freight_forwarder           ZIP list + keyword match + DB hotlist
13        bin_country_match              BIN country vs IP country (0/0.5/1.0)
14        is_vpn                         Member 5 enrichment
15        is_proxy                       Member 5 enrichment
16        is_prepaid_card                BIN lookup card_type == "prepaid"
17        merchant_risk_multiplier       MERCHANT_RISK_MULTIPLIERS[category]
18        account_age_days               (now - users.created_at).days
19        chargeback_count_90d           COUNT from chargebacks table (90-day window)
20        return_rate                    users.return_count / users.total_orders
21        total_orders                   users.total_orders
22        is_new_account                 1 if account_age_days < 7 else 0
23        amount_vs_user_avg_ratio       amount / avg(approved amounts, last 30 days)
24        is_micro_transaction           1 if amount <= 1.00 else 0
```

---

## 15. IEEE-CIS Dataset — Initial Training Data Guide

### What This Dataset Is

The IEEE-CIS Fraud Detection dataset is available on Kaggle at `https://www.kaggle.com/c/ieee-fraud-detection`. It was provided by Vesta Corporation — a real payment service provider — and contains 590,540 real e-commerce transactions with confirmed fraud labels. 3.5% of transactions are labeled as fraud (`isFraud = 1`). The remaining 96.5% are legitimate.

This is the best publicly available dataset for initial XGBoost fraud model training because it is real production data from a real payment processor, not synthetic. Top solutions on Kaggle achieved AUC-ROC above 0.92 using XGBoost on this data.

You use this dataset to train your v1 model before you have accumulated enough labeled transactions from your own platform. Once your platform has collected real chargeback labels on several thousand transactions, you retrain on your own data and the IEEE-CIS data becomes less relevant.

### File Structure

The dataset has two CSV files that you join:

`train_transaction.csv` — 590,540 rows. Contains the transaction amount, product category, card information, address fields, email domains, match flags (M1–M9), time deltas (D1–D15), counting fields (C1–C14), and the `isFraud` label column.

`train_identity.csv` — 144,233 rows (only some transactions have identity records). Contains device type, device info (browser/OS string), and anonymized identity fields (id_01 through id_38). You join this to `train_transaction.csv` on `TransactionID`.

After joining, you have a single flat table with up to ~500 columns. You will use a small fraction of them.

### Feature Mapping — What You Get and From Where

The following table shows exactly which IEEE-CIS column maps to each of your 25 features, and what status each mapping has.

| Your Feature | IEEE-CIS Column | Mapping Status | Notes |
|---|---|---|---|
| `amount` | `TransactionAmt` | **Direct** | Exact match |
| `amount_log` | `TransactionAmt` | **Derived** | Apply log(1 + x) |
| `hour_of_day` | `TransactionDT` | **Derived** | Convert seconds offset to datetime, extract hour |
| `day_of_week` | `TransactionDT` | **Derived** | Extract weekday from datetime |
| `is_weekend` | `TransactionDT` | **Derived** | weekday >= 5 |
| `card_velocity_count` | None (compute from data) | **Engineered** | Rolling count per card in 10-min window over sorted data |
| `ip_velocity_count` | None directly | **Partial** | `id_31` contains some IP info; use rolling count on card as proxy |
| `user_velocity_count` | None directly | **Engineered** | Rolling count per card in 60-min window |
| `avs_code_encoded` | `M1`, `M3` | **Approximated** | M1=T and M3=T → encode as 0 (full match); M3=F → encode as 3 (no match) |
| `cvv_missing` | Not available | **Default = 0** | Assume CVV provided for all IEEE-CIS rows |
| `billing_shipping_country_match` | `addr2`, `M1` | **Approximated** | Use addr2 (billing country code) and cross-reference with available address data |
| `billing_shipping_zip_match` | `dist1` | **Approximated** | dist1 = 0 means same location → 1; dist1 > 0 → 0 |
| `is_freight_forwarder` | Not available | **Default = 0** | No shipping address text in dataset |
| `bin_country_match` | `card3` | **Approximated** | card3 contains card country; compare against addr2 |
| `is_vpn` | `id_31` (some proxy info) | **Approximated** | Some VPN-related signals in identity file; mostly default = 0 |
| `is_proxy` | `id_31` | **Approximated** | Same as above; mostly default = 0 |
| `is_prepaid_card` | `card6` | **Direct** | card6 = "debit" → 0, card6 = "credit" → 0, card6 = "charge card" → 0; look for prepaid identifiers |
| `merchant_risk_multiplier` | `ProductCD` | **Derived** | Map W, H, C, S, R to your risk multiplier values manually |
| `account_age_days` | `D1` | **Approximated** | D1 = days between card's first transaction and current transaction |
| `chargeback_count_90d` | Not available | **Default = 0** | No chargeback history in dataset |
| `return_rate` | Not available | **Default = 0** | No return history in dataset |
| `total_orders` | Engineered | **Derived** | Rolling count of all prior transactions by card |
| `is_new_account` | `D1` | **Derived** | 1 if D1 < 7, else 0 |
| `amount_vs_user_avg_ratio` | Engineered | **Derived** | Compute rolling 30-day avg amount per card, then divide current amount |
| `is_micro_transaction` | `TransactionAmt` | **Direct** | 1 if TransactionAmt <= 1.00 |

### How to Engineer the Derived Features

**Velocity features from a static dataset:** The dataset is a flat file, not a live stream. To compute velocity, you sort the entire training dataframe by `TransactionDT` ascending. Then for each row, you look back in time at prior rows with the same card identifier (a combination of `card1` and `card4`) and count how many occurred within the relevant time window. In pandas this is done with `groupby` on the card identifier followed by a time-based rolling count. This is the same concept as your Redis sorted set but computed offline over the full dataset.

**`amount_vs_user_avg_ratio`:** Sort by `TransactionDT`. Group by card identifier. For each transaction, compute the expanding mean of all prior transaction amounts for that card within the last 30 days (in terms of `TransactionDT` seconds). Divide the current `TransactionAmt` by that mean. For the very first transaction of any card, default to 1.0.

**`ProductCD` to `merchant_risk_multiplier`:** The dataset contains five product codes: W, H, C, S, R. These are anonymized. You assign risk multipliers based on your best judgment of what these likely represent. A reasonable starting mapping: W → 1.0, H → 1.2, C → 1.4, S → 0.8, R → 0.6. These are approximate — your model will learn the pattern regardless of whether your category labels are perfect.

**`TransactionDT` to datetime:** The `TransactionDT` column is in seconds since a reference point (not a real Unix timestamp). To extract `hour_of_day`, convert it: `datetime_from_offset = datetime(2017, 12, 1) + timedelta(seconds=TransactionDT)`. The exact reference date doesn't matter for `hour_of_day` extraction as long as you are consistent.

### Features That Do Not Exist in the Dataset

Seven of your 25 features are not available in the IEEE-CIS dataset: `cvv_missing`, `is_freight_forwarder`, `is_vpn` (mostly), `is_proxy` (mostly), `chargeback_count_90d`, `return_rate`. For all of these, you fill the entire column with their default value (0 or 0.0).

**This is acceptable for initial training.** The model learns from the 18 features that are available. The 7 defaulted features contribute nothing to the initial model's predictions — they all look the same for every row. When you retrain on your own data weeks later, these features will have real values and the model will learn from them at that point.

The initial model will therefore be weaker on VPN, proxy, freight forwarder, and chargeback history signals. This is expected and acceptable. It will still perform well — the IEEE-CIS dataset achieves AUC above 0.85 with far fewer features than 25.

---

## 16. Chargeback Labeling — How the Model Learns From Real Fraud

### The Core Concept

Your ML model needs examples of both fraud (label=1) and legitimate transactions (label=0) to learn from. In a live production system, you do not have a human sitting there labeling every transaction. Instead, the labels come from chargebacks — official bank-level confirmations that a transaction was fraudulent.

Understanding this process is essential because it determines how quickly your model improves over time and why the `fraud_labels` table exists.

### What a Chargeback Is

When a fraudster uses a stolen card to buy something, the real cardholder eventually notices the charge on their bank statement. They call their bank and say "I did not make this charge." The bank investigates, confirms the charge was unauthorized, and files a chargeback. The bank forcibly reverses the payment — they take the money back from the merchant, plus a fee (typically $15–$25). The merchant loses both the product that was already shipped and the money.

The chargeback is the official, bank-confirmed proof that a specific transaction was fraud. It is your ground truth.

### The Timeline Between Transaction and Label

This is why labeling is delayed — and why you need patience before retraining produces results:

- **Day 0:** Transaction occurs. AegisFlow scores it and returns a decision.
- **Day 0–3:** If approved, the merchant ships the product.
- **Day 14–60:** The real cardholder notices the charge on their monthly statement.
- **Day 15–62:** Cardholder calls their bank to dispute the charge.
- **Day 20–90:** Bank investigates and files a formal chargeback with the merchant's payment processor.
- **Day 21–91:** The merchant's payment processor notifies the merchant of the chargeback via a webhook.
- **Day 21–91:** Member 6's backend receives the chargeback webhook, identifies the original `transaction_id`, and inserts a row into `fraud_labels`: `label=1, label_source='chargeback'`.

The typical delay between a fraud transaction and receiving the chargeback label is 30–90 days. This means your first meaningful batch of real fraud labels arrives about a month after launch.

### How Legitimate Labels Are Assigned

Fraud labels are created from chargebacks. But what about legitimate labels — how do you know a transaction was genuinely not fraud?

The answer is time-based assumption: if a transaction was approved and no chargeback arrives within 120 days, you assume it was legitimate. Member 6's backend runs a nightly job that looks for approved transactions older than 120 days with no corresponding entry in the `fraud_labels` table and inserts them with `label=0, label_source='no_chargeback_assumption'`.

This is the industry standard approach. It is not perfect — some fraud goes unreported by cardholders — but it produces a reliable training signal. The false negative rate on this labeling method is low because most cardholders do dispute unauthorized charges.

### How Labels Feed Into Weekly Retraining

Every Monday at 2 AM, the GitHub Actions retraining workflow runs. Here is what it does:

First it queries the `fraud_labels` table for all rows inserted since the last training run. These are newly confirmed fraud cases (chargebacks) and newly confirmed legitimate cases (120-day no-dispute).

For each labeled transaction, it fetches the original transaction data from the `transactions` table and runs `compute_features()` on it to reconstruct the 25-feature vector. This is exactly the same function used at inference time — training-inference consistency guaranteed.

It stacks all feature vectors into a training matrix, with labels as the target column. It adds this new data to the existing training set (or replaces it entirely — both approaches are valid, replacing is simpler).

It trains a new XGBoost model, runs cross-validation, checks that AUC is above 0.85, saves the new model files, and the next deployment picks up the new model.

### The Week-by-Week Progression

**Weeks 1–4 (initial deployment):** Your model runs on IEEE-CIS trained weights. No real chargebacks have arrived yet. The model is already useful — the 18 features it learned from IEEE-CIS data are real fraud signals. But it has not yet seen your specific merchants' fraud patterns.

**Month 2:** First chargebacks arrive. You have perhaps 50–200 confirmed fraud labels. The retraining job incorporates these. The model starts learning your platform's specific patterns — which merchant categories attract fraud, which geographies, which time patterns.

**Month 3–6:** Thousands of labeled examples have accumulated. The model starts significantly outperforming the initial IEEE-CIS model on your platform's fraud. VPN, proxy, freight forwarder, and chargeback history features now have real signal because your own transaction data includes these values.

**Month 6+:** The model has seen enough of your platform's fraud patterns that it is highly specialized to your merchant mix. At this point, the IEEE-CIS initial training data is essentially irrelevant — it has been overwhelmed by your own data. You may choose to drop it from the training set entirely to avoid the initial model's generalizations biasing your platform-specific model.

---

## 17. Layer 2 — Feature Engineering for ML

**File:** `ml/feature_engineering.py`

This is the most important file for the ML layer. It takes the raw transaction payload and all computed values (velocity counts, DB lookups, BIN data) and transforms them into the **exact 25-feature vector** that XGBoost expects.

The feature vector must be produced in the **same order and with the same transformations** as during training. If the order or transformation changes between training and inference, the model will silently produce wrong predictions.

```python
# ml/feature_engineering.py

import math
import asyncio
from datetime import datetime
from typing import Optional
from tools.fraud_patterns import (
    AVS_SCORE_MAP,
    MERCHANT_RISK_MULTIPLIERS,
    CHARGEBACK_CONFIG,
    NEW_ACCOUNT_CONFIG,
    ML_FEATURE_NAMES,
)

async def compute_features(
    payload,               # TransactionPayload
    velocity_counts: dict, # From get_velocity_features()
    bin_info: dict,        # From lookup_bin() — may be None
    db_pool,               # asyncpg pool
) -> list[float]:
    """
    Computes the full 25-feature vector for XGBoost inference.
    Returns a list of floats in the exact order defined in ML_FEATURE_NAMES.
    Missing values are filled with safe defaults (never NaN — XGBoost handles
    NaN but explicit defaults are more predictable).
    """

    # ── Async DB lookups (run concurrently) ──────────────────────────────────
    user_data, chargeback_count, user_avg_amount = await asyncio.gather(
        _get_user_data(payload.user_id, db_pool),
        _get_chargeback_count(payload.user_id, db_pool),
        _get_user_avg_amount(payload.user_id, db_pool),
    )

    # ── Temporal features ─────────────────────────────────────────────────────
    ts = payload.timestamp
    hour_of_day = ts.hour                                # 0–23
    day_of_week = ts.weekday()                           # 0=Mon, 6=Sun
    is_weekend = 1 if day_of_week >= 5 else 0

    # ── Amount features ───────────────────────────────────────────────────────
    amount = payload.amount
    amount_log = math.log1p(amount)                      # log(1 + amount) — handles skew

    # ── Velocity features (computed by Layer 1 tools) ─────────────────────────
    card_velocity_count = velocity_counts.get("card_velocity_count", 0)
    ip_velocity_count = velocity_counts.get("ip_velocity_count", 0)
    user_velocity_count = velocity_counts.get("user_velocity_count", 0)

    # ── AVS encoding ─────────────────────────────────────────────────────────
    # Encoded as ordinal: Y=0, A/Z/U=1-2, N=3
    avs_code_encoded = float(AVS_SCORE_MAP.get(payload.avs_result.upper(), 1))

    # ── CVV ───────────────────────────────────────────────────────────────────
    cvv_missing = 0.0 if payload.cvv_provided else 1.0

    # ── Address features ──────────────────────────────────────────────────────
    billing_shipping_country_match = (
        1.0 if payload.billing_country == payload.shipping_country else 0.0
    )
    billing_shipping_zip_match = (
        1.0 if payload.billing_zip == payload.shipping_zip else 0.0
    )

    # ── Freight forwarder ─────────────────────────────────────────────────────
    from tools.fraud_patterns import (
        KNOWN_FREIGHT_FORWARDER_ZIPS,
        KNOWN_FREIGHT_FORWARDER_KEYWORDS,
    )
    addr_lower = payload.shipping_address.lower()
    is_freight_forwarder = 1.0 if (
        payload.shipping_zip in KNOWN_FREIGHT_FORWARDER_ZIPS
        or any(kw in addr_lower for kw in KNOWN_FREIGHT_FORWARDER_KEYWORDS)
    ) else 0.0

    # ── BIN features ──────────────────────────────────────────────────────────
    if bin_info:
        bin_country = bin_info.get("country_code", "")
        is_prepaid = 1.0 if bin_info.get("card_type") == "prepaid" else 0.0
        # If VPN, IP country is unreliable — use 0.5 as "uncertain"
        if payload.is_vpn:
            bin_country_match = 0.5
        else:
            bin_country_match = 1.0 if (
                bin_country and bin_country == payload.ip_country
            ) else 0.0
    else:
        # BIN lookup failed — use neutral values
        bin_country_match = 0.5
        is_prepaid = 0.0

    # ── Device features ───────────────────────────────────────────────────────
    is_vpn = 1.0 if payload.is_vpn else 0.0
    is_proxy = 1.0 if payload.is_proxy else 0.0

    # ── Merchant risk ─────────────────────────────────────────────────────────
    merchant_risk_multiplier = MERCHANT_RISK_MULTIPLIERS.get(
        payload.merchant_category.lower(),
        MERCHANT_RISK_MULTIPLIERS["default"]
    )

    # ── User history features ─────────────────────────────────────────────────
    if user_data:
        account_age_days = (datetime.utcnow() - user_data["created_at"].replace(tzinfo=None)).days
        total_orders = float(user_data.get("total_orders") or 0)
        return_count = float(user_data.get("return_count") or 0)
        return_rate = (return_count / total_orders) if total_orders > 3 else 0.0
    else:
        account_age_days = 0.0
        total_orders = 0.0
        return_rate = 0.0

    is_new_account = 1.0 if account_age_days < NEW_ACCOUNT_CONFIG["age_days_threshold"] else 0.0

    # ── Amount vs. user historical average ───────────────────────────────────
    # How does this transaction compare to what this user normally spends?
    # A ratio of 10x means they're spending 10x their normal amount — suspicious.
    if user_avg_amount and user_avg_amount > 0:
        amount_vs_user_avg_ratio = amount / user_avg_amount
    else:
        amount_vs_user_avg_ratio = 1.0  # No history — neutral

    # ── Micro-transaction flag ─────────────────────────────────────────────────
    is_micro_transaction = 1.0 if amount <= 1.00 else 0.0

    # ── Assemble feature vector in ML_FEATURE_NAMES order ────────────────────
    feature_vector = [
        amount,                          # 0
        amount_log,                      # 1
        float(hour_of_day),              # 2
        float(day_of_week),              # 3
        float(is_weekend),               # 4
        float(card_velocity_count),      # 5
        float(ip_velocity_count),        # 6
        float(user_velocity_count),      # 7
        avs_code_encoded,                # 8
        cvv_missing,                     # 9
        billing_shipping_country_match,  # 10
        billing_shipping_zip_match,      # 11
        is_freight_forwarder,            # 12
        bin_country_match,               # 13
        is_vpn,                          # 14
        is_proxy,                        # 15
        is_prepaid,                      # 16
        float(merchant_risk_multiplier), # 17
        float(account_age_days),         # 18
        float(chargeback_count),         # 19
        return_rate,                     # 20
        total_orders,                    # 21
        is_new_account,                  # 22
        amount_vs_user_avg_ratio,        # 23
        is_micro_transaction,            # 24
    ]

    assert len(feature_vector) == len(ML_FEATURE_NAMES), (
        f"Feature vector length mismatch: got {len(feature_vector)}, "
        f"expected {len(ML_FEATURE_NAMES)}"
    )

    return feature_vector


# ── Private DB helpers ────────────────────────────────────────────────────────

async def _get_user_data(user_id: str, db_pool) -> Optional[dict]:
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT created_at, trust_tier, total_orders, return_count "
                "FROM users WHERE user_id = $1",
                user_id
            )
            return dict(row) if row else None
    except Exception:
        return None


async def _get_chargeback_count(user_id: str, db_pool) -> float:
    try:
        async with db_pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM chargebacks "
                "WHERE user_id = $1 AND created_at > NOW() - INTERVAL '90 days'",
                user_id
            )
            return float(count or 0)
    except Exception:
        return 0.0


async def _get_user_avg_amount(user_id: str, db_pool) -> Optional[float]:
    """
    Returns average transaction amount for this user over the last 30 days.
    Used to compute the amount_vs_user_avg_ratio feature.
    """
    try:
        async with db_pool.acquire() as conn:
            avg = await conn.fetchval(
                "SELECT AVG(amount) FROM transactions "
                "WHERE user_id = $1 "
                "AND created_at > NOW() - INTERVAL '30 days' "
                "AND status = 'approved'",
                user_id
            )
            return float(avg) if avg else None
    except Exception:
        return None
```

-----

## 13. Layer 2 — XGBoost Model Training Pipeline

**File:** `ml/model_trainer.py`

**This script runs OFFLINE — not during API request handling.** Run it manually before first deployment and weekly thereafter via a scheduled job (cron or GitHub Actions). It reads historical labeled transactions from PostgreSQL, trains the XGBoost model, and saves the model files to the `models/` directory.

```python
# ml/model_trainer.py
# Run: python -m ml.model_trainer

import asyncpg
import asyncio
import numpy as np
import pandas as pd
import xgboost as xgb
import joblib
import json
import shap
from datetime import datetime
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, classification_report
from tools.fraud_patterns import ML_FEATURE_NAMES
import os

MODEL_DIR = "models"
MODEL_VERSION = "v1"


async def load_training_data(db_url: str) -> pd.DataFrame:
    """
    Loads labeled transactions from PostgreSQL.
    Joins transactions with fraud_labels to get ground truth.
    Only loads transactions where a definitive label exists.
    """
    conn = await asyncpg.connect(db_url)
    rows = await conn.fetch(
        """
        SELECT
            t.transaction_id,
            t.amount,
            EXTRACT(HOUR FROM t.created_at) AS hour_of_day,
            EXTRACT(DOW FROM t.created_at) AS day_of_week,
            t.user_id,
            fl.label
        FROM transactions t
        INNER JOIN fraud_labels fl USING (transaction_id)
        WHERE fl.label IN (0, 1)
        ORDER BY t.created_at DESC
        LIMIT 500000
        """
    )
    await conn.close()
    return pd.DataFrame(rows, columns=[
        "transaction_id", "amount", "hour_of_day", "day_of_week",
        "user_id", "label"
    ])


def build_feature_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    NOTE: In production, the feature matrix is built using the same
    compute_features() function used at inference time. The training
    pipeline should iterate over each transaction and call compute_features()
    to guarantee consistency.

    For simplicity here we show the structure. In practice:
    1. Fetch raw transactions with their labels from the DB
    2. For each transaction, reconstruct the payload object
    3. Call compute_features() asynchronously
    4. Stack results into a matrix

    This guarantees training-inference consistency — the single most
    important property to maintain in an ML fraud system.
    """
    # Placeholder — replace with actual feature computation loop
    X = df[["amount", "hour_of_day", "day_of_week"]].values.astype(float)
    y = df["label"].values.astype(int)
    return X, y


def train_model(X: np.ndarray, y: np.ndarray) -> xgb.XGBClassifier:
    """
    Trains an XGBoost classifier optimized for fraud detection.

    Key parameters explained:
    - scale_pos_weight: Fraud is ~0.1–1% of transactions (severe class imbalance).
      This weight tells XGBoost to penalize missing fraud cases much more heavily
      than missing legitimate cases. Set to (negative_count / positive_count).
    - max_depth=6: Deep enough to capture complex interactions, not so deep it
      overfits. Fraud features interact in complex ways — depth is needed.
    - n_estimators=300: 300 trees. More trees = better accuracy up to a point.
      Use early stopping to find the real optimal number.
    - learning_rate=0.05: Slow learning rate with more trees → better generalization.
    - subsample=0.8: Train each tree on 80% of data → reduces overfitting.
    - colsample_bytree=0.8: Each tree sees 80% of features → reduces correlation.
    - eval_metric='aucpr': AUC-PR (area under precision-recall curve) is better
      than AUC-ROC for imbalanced datasets like fraud detection. We care about
      precision at high recall, not overall accuracy.
    """
    n_negative = (y == 0).sum()
    n_positive = (y == 1).sum()
    scale_pos_weight = n_negative / max(n_positive, 1)

    print(f"Training on {len(y)} samples: {n_positive} fraud, {n_negative} legitimate")
    print(f"scale_pos_weight: {scale_pos_weight:.1f}")

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        use_label_encoder=False,
        tree_method="hist",          # Fast training
        random_state=42,
        n_jobs=-1,
    )

    # Stratified cross-validation to measure real performance
    # Stratified = maintains fraud ratio in each fold (important for imbalanced data)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=skf, scoring="roc_auc")
    print(f"Cross-validation AUC-ROC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Train final model on all data
    model.fit(X, y)
    return model


def save_artifacts(model: xgb.XGBClassifier, X_sample: np.ndarray, metrics: dict):
    """
    Saves all model artifacts to the models/ directory.
    Three files are saved:
    - xgboost_fraud_{version}.pkl: The trained model
    - shap_explainer_{version}.pkl: SHAP TreeExplainer pre-built on the model
    - model_metadata.json: Version, training date, metrics
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Save model
    model_path = f"{MODEL_DIR}/xgboost_fraud_{MODEL_VERSION}.pkl"
    joblib.dump(model, model_path)
    print(f"Model saved: {model_path}")

    # Build and save SHAP explainer
    # TreeExplainer is the fastest SHAP method for tree-based models
    # It computes exact Shapley values (not approximations) in O(TLD) time
    explainer = shap.TreeExplainer(model)
    explainer_path = f"{MODEL_DIR}/shap_explainer_{MODEL_VERSION}.pkl"
    joblib.dump(explainer, explainer_path)
    print(f"SHAP explainer saved: {explainer_path}")

    # Save metadata
    metadata = {
        "version": MODEL_VERSION,
        "trained_at": datetime.utcnow().isoformat(),
        "n_features": len(ML_FEATURE_NAMES),
        "feature_names": ML_FEATURE_NAMES,
        "model_file": f"xgboost_fraud_{MODEL_VERSION}.pkl",
        "explainer_file": f"shap_explainer_{MODEL_VERSION}.pkl",
        "metrics": metrics,
    }
    with open(f"{MODEL_DIR}/model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved: {MODEL_DIR}/model_metadata.json")


async def main():
    db_url = os.environ["DATABASE_URL"]
    print("Loading training data...")
    df = await load_training_data(db_url)

    X, y = build_feature_matrix(df)
    print(f"Feature matrix shape: {X.shape}")

    model = train_model(X, y)

    # Evaluate on training set (just for reporting — real eval is in CV above)
    y_pred_prob = model.predict_proba(X)[:, 1]
    auc = roc_auc_score(y, y_pred_prob)
    print(f"Training AUC-ROC: {auc:.4f}")
    print(classification_report(y, model.predict(X), target_names=["Legit", "Fraud"]))

    save_artifacts(model, X[:100], {"train_auc": round(auc, 4)})
    print("Training complete.")


if __name__ == "__main__":
    asyncio.run(main())
```

-----

## 14. Layer 2 — ML Inference (Real-Time)

**File:** `ml/model_inference.py`

This runs in the hot path — every transaction goes through this. Load the model once at startup. Do not reload it on each request.

```python
# ml/model_inference.py

import joblib
import json
import numpy as np
from typing import Optional
import asyncio

_model = None
_metadata = None
MODEL_AVAILABLE = False

MODEL_PATH = "models/xgboost_fraud_v1.pkl"
METADATA_PATH = "models/model_metadata.json"


def load_model():
    """
    Called once at application startup (in main.py).
    Loads the XGBoost model and metadata into memory.
    Sets MODEL_AVAILABLE = True if successful.
    """
    global _model, _metadata, MODEL_AVAILABLE
    try:
        _model = joblib.load(MODEL_PATH)
        with open(METADATA_PATH) as f:
            _metadata = json.load(f)
        MODEL_AVAILABLE = True
        print(
            f"[ML] Model loaded: version={_metadata['version']}, "
            f"trained_at={_metadata['trained_at']}"
        )
    except FileNotFoundError:
        MODEL_AVAILABLE = False
        print("[ML] WARNING: Model file not found. Running in rule-only mode.")
    except Exception as e:
        MODEL_AVAILABLE = False
        print(f"[ML] WARNING: Model load failed: {e}. Running in rule-only mode.")


async def predict(feature_vector: list[float]) -> dict:
    """
    Runs XGBoost inference on the 25-feature vector.
    Returns fraud probability (0.0–1.0) and a 0-100 score.

    XGBoost is synchronous — wrap in asyncio.to_thread() to avoid
    blocking the event loop. Inference is ~1–3ms on CPU.

    Returns:
        {
            "fraud_probability": float,   # 0.0 – 1.0
            "ml_score": int,              # 0 – 100
            "model_version": str,
        }
    """
    if not MODEL_AVAILABLE or _model is None:
        return {
            "fraud_probability": 0.5,
            "ml_score": 50,
            "model_version": "unavailable",
            "error": "model_not_loaded",
        }

    X = np.array(feature_vector, dtype=float).reshape(1, -1)

    # Run in thread pool to avoid blocking async event loop
    fraud_prob = await asyncio.to_thread(
        lambda: float(_model.predict_proba(X)[0, 1])
    )

    # Scale probability to 0–100 score
    # We use a non-linear mapping: the first 50% of probability maps to 0–70 score,
    # the top 50% maps to 70–100. This gives more resolution at the high-risk end
    # where precise differentiation matters most.
    if fraud_prob < 0.5:
        ml_score = int(fraud_prob * 140)        # 0.0–0.5 → 0–70
    else:
        ml_score = int(70 + (fraud_prob - 0.5) * 60)  # 0.5–1.0 → 70–100

    ml_score = min(ml_score, 100)

    return {
        "fraud_probability": round(fraud_prob, 4),
        "ml_score": ml_score,
        "model_version": _metadata.get("version", "unknown"),
        "error": None,
    }
```

-----

## 15. Layer 2 — SHAP Explainability

**File:** `ml/shap_explainer.py`

SHAP generates a human-readable explanation for every ML prediction. This is required for Member 8’s compliance audit trail and for customer-facing dispute resolution.

```python
# ml/shap_explainer.py

import joblib
import numpy as np
import asyncio
from typing import Optional
from tools.fraud_patterns import ML_FEATURE_NAMES

_explainer = None
EXPLAINER_AVAILABLE = False

EXPLAINER_PATH = "models/shap_explainer_v1.pkl"


def load_explainer():
    """Called once at startup alongside load_model()."""
    global _explainer, EXPLAINER_AVAILABLE
    try:
        _explainer = joblib.load(EXPLAINER_PATH)
        EXPLAINER_AVAILABLE = True
        print("[SHAP] Explainer loaded.")
    except Exception as e:
        EXPLAINER_AVAILABLE = False
        print(f"[SHAP] WARNING: Explainer load failed: {e}")


async def explain(feature_vector: list[float], top_n: int = 5) -> Optional[dict]:
    """
    Generates a SHAP explanation for a single prediction.
    Returns the top N features by absolute SHAP contribution.

    A positive SHAP value means this feature pushed the score TOWARD fraud.
    A negative SHAP value means this feature pushed the score AWAY from fraud.

    Example output:
    {
        "top_features": [
            {"feature": "is_freight_forwarder", "contribution": 0.41, "value": 1.0},
            {"feature": "card_velocity_count",  "contribution": 0.23, "value": 5.0},
            {"feature": "cvv_missing",          "contribution": 0.18, "value": 1.0},
            {"feature": "avs_code_encoded",     "contribution": 0.14, "value": 3.0},
            {"feature": "bin_country_match",    "contribution": -0.08, "value": 1.0},
        ]
    }
    """
    if not EXPLAINER_AVAILABLE or _explainer is None:
        return None

    X = np.array(feature_vector, dtype=float).reshape(1, -1)

    # SHAP TreeExplainer is fast (~5–15ms) but still sync
    shap_values = await asyncio.to_thread(
        lambda: _explainer.shap_values(X)[0]  # Shape: (n_features,)
    )

    # Pair feature names with their SHAP values
    feature_contributions = [
        {
            "feature": name,
            "contribution": round(float(sv), 4),
            "value": round(float(feature_vector[i]), 4),
        }
        for i, (name, sv) in enumerate(zip(ML_FEATURE_NAMES, shap_values))
    ]

    # Sort by absolute contribution (most impactful first)
    feature_contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)

    return {"top_features": feature_contributions[:top_n]}
```

-----

## 16. Score Combination Logic

The final score that goes to the Orchestrator is composed as follows:

### Case 1 — Hard Block Fired (Layer 1)

```
final_score = 100
hard_blocked = True
ml_fraud_probability = 0.0   ← ML was never called
shap_explanation = None      ← No SHAP needed (rule was decisive)
```

### Case 2 — Normal Flow (Layer 2 ML)

```
ml_score = output of predict() — already 0–100
soft_rule_flags = flags from velocity/AVS/address soft checks
final_score = ml_score    ← ML score IS the final score
                           The soft rule signals were features
                           that influenced the ML score —
                           do NOT add them separately on top.
```

**Why you don’t add rule scores on top of ML scores:**
The soft rule checks (velocity counts, AVS encoding, address mismatch) are already **fed as features into XGBoost**. XGBoost has already factored them into `ml_score`. Adding them again would be double-counting. The only additive layer is the hard block (which bypasses ML entirely).

### Soft Rule Flags (for transparency)

Even though soft rules don’t add to the score, they should still appear in the `flags` list if their values exceed the soft thresholds. This is for Member 8’s explainability. The SHAP explanation shows *how much* they contributed; the flags show *which ones were elevated*.

```python
def compute_soft_flags(velocity_counts: dict, avs_result: str,
                        billing_country: str, shipping_country: str) -> list[str]:
    flags = []
    cfg = SOFT_VELOCITY_THRESHOLDS
    if velocity_counts["card_velocity_count"] > cfg["card"]["max_attempts"]:
        flags.append("card_velocity_elevated")
    if velocity_counts["ip_velocity_count"] > cfg["ip"]["max_attempts"]:
        flags.append("ip_velocity_elevated")
    if velocity_counts["user_velocity_count"] > cfg["user"]["max_attempts"]:
        flags.append("user_velocity_elevated")
    if avs_result.upper() == "N":
        flags.append("avs_no_match")
    elif avs_result.upper() in ("Z", "A"):
        flags.append("avs_partial_match")
    if billing_country != shipping_country:
        flags.append("address_country_mismatch")
    return flags
```

-----

## 17. Model Versioning & Retraining

### Versioning Convention

Every trained model has a version string (v1, v2, v3…) stored in `model_metadata.json`. When you retrain:

1. Increment the version number in `model_trainer.py`
1. Run the trainer — it saves new `.pkl` files with the new version
1. Update `MODEL_PATH` in `model_inference.py` to point to the new file
1. Restart the application — `load_model()` at startup picks up the new file

> **Do not delete old model files.** Keep at least 2 previous versions so you can roll back if the new model performs worse in production.

### Retraining Schedule

Retrain the model weekly using a scheduled job. Trigger it every Monday at 2 AM UTC via GitHub Actions or cron:

```yaml
# .github/workflows/retrain_model.yml
name: Weekly Model Retrain
on:
  schedule:
    - cron: '0 2 * * 1'   # Every Monday at 2 AM UTC
jobs:
  retrain:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run trainer
        run: python -m ml.model_trainer
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### When to Retrain Immediately (Not Just Weekly)

- Sudden spike in false positives reported by customers
- New fraud pattern detected that your current model is missing
- You’ve collected 5,000+ new labeled fraud cases since the last training
- Model AUC-ROC drops below 0.85 (monitor this with Grafana via Member 7)

### Monitoring Model Drift

Add these two metrics to Grafana (coordinate with Member 7):

1. **Average daily fraud_probability score** — if this drifts up steadily, fraudsters are finding new patterns
1. **False positive rate** — estimated as (transactions blocked but later disputed by real customers) / (total blocked). If this exceeds 2%, the model is too aggressive

-----

## 18. Transaction Agent — Main Orchestration Logic

**File:** `agents/transaction_agent.py`

```python
# agents/transaction_agent.py

import asyncio
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from tools.velocity_checker import (
    init_redis,
    check_extreme_velocity,
    check_card_testing_hard_block,
    check_freight_forwarder_hard_block,
    check_cvv_avs_combined_hard_block,
    get_velocity_features,
)
from ml.feature_engineering import compute_features
from ml.model_inference import predict, load_model, MODEL_AVAILABLE
from ml.shap_explainer import explain, load_explainer
from services.bin_lookup import lookup_bin
from tools.fraud_patterns import (
    VALID_FLAGS,
    MERCHANT_RISK_MULTIPLIERS,
    HIGH_RISK_MERCHANT_THRESHOLD,
)

# Pydantic models from Section 7 go here

db_pool = None

def init_db(pool):
    global db_pool
    db_pool = pool

def startup():
    """Call this in main.py at application startup."""
    load_model()
    load_explainer()


async def analyze(payload: TransactionPayload) -> TransactionAgentResult:
    """
    Main entry point. Called by Member 2's Orchestrator.
    Executes the two-layer hybrid fraud detection pipeline.
    Total latency target: < 200ms.
    """
    try:
        # ────────────────────────────────────────────────────────────────────
        # LAYER 1 — HARD RULE CHECKS
        # Run ALL hard rules first. If any fires, return immediately.
        # ML is never called on a hard block.
        # ────────────────────────────────────────────────────────────────────

        # Run hard rule checks concurrently where possible
        extreme_vel = await asyncio.to_thread(
            check_extreme_velocity,
            payload.card_bin, payload.card_last4, payload.transaction_id
        )
        card_test = await asyncio.to_thread(
            check_card_testing_hard_block,
            payload.ip_address, payload.transaction_id, payload.amount
        )
        freight = await asyncio.to_thread(
            check_freight_forwarder_hard_block,
            payload.shipping_zip, payload.shipping_address
        )
        cvv_avs = check_cvv_avs_combined_hard_block(
            payload.cvv_provided, payload.avs_result
        )

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
            return TransactionAgentResult(
                agent="transaction_agent",
                score=100,
                flags=[hard_block_flag],
                hard_blocked=True,
                ml_fraud_probability=0.0,
                shap_explanation=None,
                check_details={"hard_block_reason": hard_block_flag},
                error=None,
            )

        # ────────────────────────────────────────────────────────────────────
        # LAYER 2 — ML SCORING
        # Step 1: Compute velocity features (needed for both flags and features)
        # Step 2: Fetch BIN data (async, external)
        # Step 3: Compute full feature vector
        # Step 4: ML inference
        # Step 5: SHAP explanation
        # Step 6: Compute soft flags (for transparency)
        # ────────────────────────────────────────────────────────────────────

        # Step 1 & 2 run concurrently
        velocity_counts, bin_info = await asyncio.gather(
            asyncio.to_thread(
                get_velocity_features,
                payload.card_bin, payload.card_last4,
                payload.ip_address, payload.user_id,
                payload.transaction_id
            ),
            lookup_bin(payload.card_bin),
        )

        # Step 3: Feature engineering
        feature_vector = await compute_features(
            payload, velocity_counts, bin_info, db_pool
        )

        # Steps 4 & 5: ML inference and SHAP (run concurrently)
        ml_result, shap_result = await asyncio.gather(
            predict(feature_vector),
            explain(feature_vector),
        )

        final_score = ml_result["ml_score"]
        ml_flag = []
        if not MODEL_AVAILABLE:
            ml_flag = ["ml_model_unavailable"]

        # Step 6: Compute soft flags for transparency
        soft_flags = compute_soft_flags(
            velocity_counts,
            payload.avs_result,
            payload.billing_country,
            payload.shipping_country,
        )

        # Add merchant category flag if high risk
        category = payload.merchant_category.lower()
        multiplier = MERCHANT_RISK_MULTIPLIERS.get(category, 1.0)
        category_flags = (
            ["high_risk_merchant_category"]
            if multiplier >= HIGH_RISK_MERCHANT_THRESHOLD
            else []
        )

        # Add VPN flag
        vpn_flags = ["vpn_detected"] if payload.is_vpn else []

        # Combine all flags, deduplicate, validate
        all_flags = list(set(
            soft_flags + category_flags + vpn_flags + ml_flag
        ))
        all_flags = [f for f in all_flags if f in VALID_FLAGS]

        return TransactionAgentResult(
            agent="transaction_agent",
            score=final_score,
            flags=all_flags,
            hard_blocked=False,
            ml_fraud_probability=ml_result["fraud_probability"],
            shap_explanation=shap_result,
            check_details={
                "velocity_counts": velocity_counts,
                "bin_info": bin_info,
                "ml_score": ml_result["ml_score"],
                "model_version": ml_result["model_version"],
                "feature_vector_length": len(feature_vector),
            },
            error=None,
        )

    except Exception as e:
        return TransactionAgentResult(
            agent="transaction_agent",
            score=50,
            flags=["agent_error"],
            hard_blocked=False,
            ml_fraud_probability=0.5,
            shap_explanation=None,
            check_details={"error": str(e)},
            error=str(e),
        )
```

-----

## 19. Output Contract — What You Return to the Orchestrator

This is the exact JSON shape. Member 2 will deserialize this. Do not change field names.

```json
{
  "agent": "transaction_agent",
  "score": 82,
  "flags": ["card_velocity_elevated", "high_risk_merchant_category", "vpn_detected"],
  "hard_blocked": false,
  "ml_fraud_probability": 0.7943,
  "shap_explanation": {
    "top_features": [
      {"feature": "card_velocity_count",        "contribution": 0.31, "value": 6.0},
      {"feature": "merchant_risk_multiplier",   "contribution": 0.22, "value": 1.4},
      {"feature": "is_vpn",                     "contribution": 0.19, "value": 1.0},
      {"feature": "avs_code_encoded",           "contribution": 0.11, "value": 2.0},
      {"feature": "amount_vs_user_avg_ratio",   "contribution": 0.08, "value": 8.3}
    ]
  },
  "check_details": {
    "velocity_counts": {"card_velocity_count": 6, "ip_velocity_count": 2, "user_velocity_count": 1},
    "bin_info": {"country_code": "US", "card_type": "credit", "card_brand": "visa"},
    "ml_score": 82,
    "model_version": "v1",
    "feature_vector_length": 25
  },
  "error": null
}
```

**Hard block example:**

```json
{
  "agent": "transaction_agent",
  "score": 100,
  "flags": ["hard_block_card_testing"],
  "hard_blocked": true,
  "ml_fraud_probability": 0.0,
  "shap_explanation": null,
  "check_details": {"hard_block_reason": "hard_block_card_testing"},
  "error": null
}
```

-----

## 20. Error Handling Rules

|Situation                                    |Behavior                                                                                                                                                |
|---------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
|Hard rule check throws exception             |Log error, treat that specific hard rule as not-fired. Continue to other hard rules.                                                                    |
|Redis is down                                |Fall back to PostgreSQL count for velocity. If both fail, set velocity counts to 0 (safe default). Log warning.                                         |
|BIN API times out (>2 seconds)               |Set `bin_info = None`. Feature engineering handles None with neutral defaults.                                                                          |
|DB query fails in feature engineering        |Set affected features to safe defaults (0 for counts, 0.5 for ratios). Log error.                                                                       |
|ML model file not found at startup           |`MODEL_AVAILABLE = False`. Agent runs in rule-only mode. All ML scores = 50. Add `ml_model_unavailable` flag. Alert Member 7 to investigate.            |
|XGBoost inference throws exception           |Return `ml_score=50`, add `agent_error` flag. Do NOT crash.                                                                                             |
|SHAP explainer fails                         |Return `shap_explanation=None`. This is non-critical — score is still valid.                                                                            |
|Entire `analyze()` throws unhandled exception|Catch in top-level try/except. Return `score=50`, `flags=["agent_error"]`. Never return score=0 (passes fraud through) or score=100 (blocks real users).|
|Feature vector length mismatch               |This means training/inference inconsistency. Raise a startup error loud enough to stop deployment. Do not silently proceed.                             |

-----

## 21. Test Cases

**File:** `tests/test_transaction_agent.py`

```python
# tests/test_transaction_agent.py

import pytest
from datetime import datetime
from agents.transaction_agent import analyze, TransactionPayload

def make_payload(**overrides) -> TransactionPayload:
    defaults = {
        "transaction_id": "txn_test_001",
        "user_id": "usr_trusted_001",
        "timestamp": datetime.utcnow(),
        "card_bin": "411111",
        "card_last4": "4242",
        "amount": 50.0,
        "currency": "USD",
        "cvv_provided": True,
        "avs_result": "Y",
        "billing_address": "123 Main St, Karachi",
        "billing_country": "PK",
        "billing_zip": "75500",
        "shipping_address": "123 Main St, Karachi",
        "shipping_country": "PK",
        "shipping_zip": "75500",
        "merchant_id": "merch_001",
        "merchant_category": "clothing",
        "ip_address": "103.45.67.89",
        "ip_country": "PK",
        "is_vpn": False,
        "is_proxy": False,
    }
    defaults.update(overrides)
    return TransactionPayload(**defaults)


# Test 1: Clean transaction should not be hard blocked
@pytest.mark.asyncio
async def test_clean_transaction_not_hard_blocked():
    result = await analyze(make_payload())
    assert result.hard_blocked is False
    assert result.error is None
    assert result.agent == "transaction_agent"


# Test 2: CVV missing + AVS=N must hard block
@pytest.mark.asyncio
async def test_cvv_avs_combined_hard_block():
    result = await analyze(make_payload(cvv_provided=False, avs_result="N"))
    assert result.hard_blocked is True
    assert result.score == 100
    assert "hard_block_cvv_and_avs_fail" in result.flags
    assert result.shap_explanation is None  # No SHAP on hard block


# Test 3: Freight forwarder ZIP must hard block
@pytest.mark.asyncio
async def test_freight_forwarder_hard_block():
    result = await analyze(make_payload(
        shipping_zip="33166",
        shipping_address="8700 NW 36th St, Miami, FL",
        shipping_country="US",
    ))
    assert result.hard_blocked is True
    assert "hard_block_freight_forwarder" in result.flags


# Test 4: Freight forwarder keyword in address must hard block
@pytest.mark.asyncio
async def test_freight_forwarder_keyword_hard_block():
    result = await analyze(make_payload(
        shipping_address="Suite 400, The UPS Store, 123 Commerce Blvd, Miami, FL",
        shipping_zip="99999",  # Not in the ZIP list, but keyword match
    ))
    assert result.hard_blocked is True


# Test 5: ML model unavailable flag appears when model not loaded
@pytest.mark.asyncio
async def test_ml_unavailable_flag(monkeypatch):
    import ml.model_inference as mi
    monkeypatch.setattr(mi, "MODEL_AVAILABLE", False)
    result = await analyze(make_payload())
    assert "ml_model_unavailable" in result.flags
    assert result.ml_fraud_probability == 0.5


# Test 6: Agent must never crash — returns score=50 on exception
@pytest.mark.asyncio
async def test_agent_safe_fallback_on_exception(monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("Simulated failure")
    monkeypatch.setattr("agents.transaction_agent.compute_features", broken)
    result = await analyze(make_payload())
    assert result.score == 50
    assert result.error is not None
    assert "agent_error" in result.flags


# Test 7: Output shape is always complete and valid
@pytest.mark.asyncio
async def test_output_shape_is_complete():
    result = await analyze(make_payload())
    assert isinstance(result.score, int)
    assert 0 <= result.score <= 100
    assert isinstance(result.flags, list)
    assert isinstance(result.hard_blocked, bool)
    assert isinstance(result.ml_fraud_probability, float)
    assert 0.0 <= result.ml_fraud_probability <= 1.0
    assert result.check_details is not None


# Test 8: Feature vector has exactly 25 features
@pytest.mark.asyncio
async def test_feature_vector_length(monkeypatch):
    captured = []
    original_predict = __import__("ml.model_inference", fromlist=["predict"]).predict

    async def capturing_predict(features):
        captured.append(features)
        return await original_predict(features)

    monkeypatch.setattr("agents.transaction_agent.predict", capturing_predict)
    await analyze(make_payload())

    if captured:  # Only runs if model is available
        assert len(captured[0]) == 25


# File: tests/test_feature_engineering.py

@pytest.mark.asyncio
async def test_feature_vector_length_unit():
    from ml.feature_engineering import compute_features
    payload = make_payload()
    velocity = {"card_velocity_count": 1, "ip_velocity_count": 1, "user_velocity_count": 1}
    features = await compute_features(payload, velocity, None, None)
    assert len(features) == 25


@pytest.mark.asyncio
async def test_all_features_are_finite():
    import math
    from ml.feature_engineering import compute_features
    payload = make_payload()
    velocity = {"card_velocity_count": 0, "ip_velocity_count": 0, "user_velocity_count": 0}
    features = await compute_features(payload, velocity, None, None)
    for i, f in enumerate(features):
        assert math.isfinite(f), f"Feature index {i} is not finite: {f}"
```

-----

## 22. Integration Checklist

### With Member 6 (Backend)

- [ ] `REDIS_URL` environment variable is set and Redis is reachable
- [ ] `DATABASE_URL` environment variable is set and PostgreSQL is reachable
- [ ] `fraud_labels` table created (see Section 9)
- [ ] `init_redis()` called in `main.py` before first request
- [ ] `init_db(pool)` called in `main.py` with asyncpg pool
- [ ] `startup()` called in `main.py` (loads model + SHAP explainer)

### With Member 5 (Device Agent)

- [ ] Confirmed field names: `ip_address`, `ip_country`, `is_vpn`, `is_proxy`
- [ ] When Member 5 fields are absent, defaults are applied (not crash)

### With Member 2 (Orchestrator)

- [ ] Shared `TransactionPayload` input schema (Section 7.1)
- [ ] Shared `TransactionAgentResult` output schema (Section 7.2 + 19)
- [ ] Entry point is `analyze(payload: TransactionPayload)` — async
- [ ] Agent completes within **200ms** latency budget

### With Member 8 (Guardrail)

- [ ] `shap_explanation.top_features` is populated for all non-hard-block decisions
- [ ] `check_details` dict is populated for every transaction
- [ ] `VALID_FLAGS` list shared — Member 8 validates against it
- [ ] Hard blocked transactions return `shap_explanation=None` (Member 8 handles this case)

### ML Model

- [ ] `python -m ml.model_trainer` runs successfully against staging DB
- [ ] Model files exist in `models/` directory before deployment
- [ ] `model_metadata.json` contains correct version, feature names, and metrics
- [ ] Feature vector length assertion passes (`len == 25`)
- [ ] Model AUC-ROC is above 0.85 before deploying to production

### Code Quality

- [ ] All 8 test cases pass
- [ ] No hardcoded credentials — secrets via environment variables only
- [ ] BIN API timeout is set to 2 seconds (hard maximum)
- [ ] No unhandled exceptions propagate out of `analyze()`
- [ ] Feature engineering uses identical transformations as training script

-----

*End of Document — AegisFlow AI, Member 3 Transaction Fraud Engineer Hybrid Specification v2.0*