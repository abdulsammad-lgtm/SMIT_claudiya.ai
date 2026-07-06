# Claudiya.ai — Full Project Specification

## Complete Workflow, Member Roles & System Flow

> **Document Type:** Product Requirements Document (PRD)  
> **Purpose:** Complete project understanding for every team member  
> **Product:** Claudiya.ai — Real-Time Multi-Agent Fraud Detection Platform  
> **This document contains no code.** For implementation details, refer to per-member implementation guides and the source code.

-----

## Table of Contents

1. [What Claudiya.ai Is](#1-what-claudiyaai-is)
1. [How the Business Works](#2-how-the-business-works)
1. [Complete System Architecture](#3-complete-system-architecture)
1. [The Complete Transaction Flow — From Pay Button to Decision](#4-the-complete-transaction-flow--from-pay-button-to-decision)
   - Phase 1: Customer Initiates Checkout
   - Phase 2: Merchant Backend Calls Claudiya.ai
   - Phase 3: API Authentication & Validation
   - Phase 4: Orchestrator Fires All Agents
   - Phase 5: Device Agent Runs
   - Phase 6: Behavioral Agent Runs
   - Phase 7: Network Agent Runs
   - Phase 8: Transaction Agent Runs
   - Phase 9: Behavioral Bio Agent Runs
   - Phase 10: Composite Scoring
   - Phase 11: Guardrail Validation
   - Phase 12: Response Returned to Merchant
   - Phase 13: Merchant Acts on Decision
   - Phase 14: Dashboard Updated in Real Time
1. [Member 1 — Team Lead / AI Architect](#5-member-1--team-lead--ai-architect)
1. [Member 2 — Orchestrator Engineer](#6-member-2--orchestrator-engineer)
1. [Member 3 — Transaction Fraud Engineer](#7-member-3--transaction-fraud-engineer)
1. [Member 4 — Behavioral AI Engineer](#8-member-4--behavioral-ai-engineer)
1. [Member 5 — Device & Network Security Engineer](#9-member-5--device--network-security-engineer)
1. [Member 6 — Backend API Engineer](#10-member-6--backend-api-engineer)
1. [Member 7 — DevOps, Deployment & Compliance Engineer](#11-member-7-devops-deployment--compliance-engineer)
1. [Database Design](#12-database-design)
1. [Inter-Member Dependency Map](#13-inter-member-dependency-map)
1. [GitHub Workflow & Branching](#14-github-workflow--branching)
1. [Testing Requirements](#15-testing-requirements)
1. [Launch Checklist](#16-launch-checklist)

-----

## 1. What Claudiya.ai Is

Claudiya.ai is a production-grade, real-time fraud detection platform that e-commerce businesses integrate into their checkout flow. When a customer clicks "Pay" on any merchant's website, the merchant's system calls Claudiya.ai's API in the background. Within 200 milliseconds, Claudiya.ai analyzes that transaction using a five-agent AI pipeline and returns a fraud risk decision. The merchant uses that decision to either approve the order, decline it, or hold it for manual review.

Unlike traditional fraud detection systems that rely on simple rule engines, Claudiya.ai uses five parallel specialist agents — Device, Behavior, Network, Transaction, and Behavioral Bio — each analyzing a different dimension of the transaction. These agents run simultaneously, their outputs are fused using configurable composite scoring strategies, and every decision passes through an LLM-powered compliance guardrail before being returned.

Claudiya.ai is not a product that end customers see or interact with. It operates silently in the background of any checkout process that a merchant has integrated it into. The platform also provides a web dashboard for merchant fraud analysts to review transactions, monitor agent health, and override decisions where necessary.

**Tagline:** *Five agents. One verdict. Zero blind spots.*

-----

## 2. How the Business Works

Claudiya.ai operates as a B2B SaaS platform. The customers of Claudiya.ai are not the people shopping online — they are the e-commerce businesses running those shops. Every e-commerce business that signs up for Claudiya.ai is called a **merchant**.

Each merchant gets an API key when they sign up. Their development team uses that key to connect their checkout backend to Claudiya.ai. Every transaction their customers attempt gets sent to Claudiya.ai for analysis. Merchants pay based on how many transactions they analyze per month.

Merchants also get access to a web dashboard where they can log in and see a live feed of all their transactions, review fraud decisions, override specific decisions where they disagree, and monitor the health and performance of each fraud detection agent in real time.

This means Claudiya.ai has two interfaces:

- A **machine-to-machine API** used by merchant servers (authenticated with API keys)
- A **human-facing dashboard** used by merchant analysts and admins (authenticated with JWT tokens)

These are two completely separate authentication systems with separate security requirements. The API uses SHA-256 hashed API keys for server-to-server communication. The dashboard uses email/password login with bcrypt password hashing and JWT access/refresh tokens (30-minute access token expiry, 7-day refresh token expiry).

### Agent Scoring Modes

Claudiya.ai supports three composite scoring strategies that merchants can choose from:

| Mode | Description | Use Case |
|------|-------------|----------|
| Weighted | Linear weighted average of all 5 agent scores | Default — balanced across all signals |
| Max | Highest single agent score determines outcome | Conservative — catch the strongest signal |
| Ensemble | Weighted combination of Weighted (70%) and Max (30%) | Hybrid — balance between average and worst-case |

### Execution Modes

Each transaction can be scored through one of three execution paths:

| Mode | Description | Latency Target |
|------|-------------|----------------|
| Fast Path | Deterministic scoring from tool function outputs — no LLM call | Under 150ms |
| Reasoning Path | Full OpenAI Agents SDK agent loop with natural-language explanations | Under 500ms |
| Hybrid Path | Fast path first, then LLM reasoning for high-risk agents (score > 30) | Under 300ms |

### Decision Thresholds

| Score Range | Decision | Meaning |
|-------------|----------|---------|
| 0 – 29 | approve | Transaction is clean — proceed with payment |
| 30 – 69 | review | Uncertain — hold for human analyst review |
| 70 – 100 | decline | High risk — reject transaction |

-----

## 3. Complete System Architecture

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                              CLIENT SIDE                                      ║
║                                                                              ║
║  React Dashboard (TanStack Start + Vite)                                     ║
║  ┌──────────────────────────────────────────────────────────────────┐       ║
║  │  Routes: / (Dashboard), /auth, /progress, /admin                 │       ║
║  │  /agents/orchestrator, /agents/behavior, /agents/device          │       ║
║  │                                                                  │       ║
║  │  Components: StatCard, RiskChart, ThreatFeed, AgentProgress      │       ║
║  │  AgentPage, AgentExtras, Guardrails, TopBar, AppSidebar          │       ║
║  │                                                                  │       ║
║  │  State: TanStack Query (5s polling), React useState              │       ║
║  │  Styling: Tailwind v4 + shadcn/ui + Framer Motion animations     │       ║
║  └──────────────────────────────────────────────────────────────────┘       ║
╚══════════════════════════════════════════════════════════════════════════════╝
                              │ HTTP REST + WebSocket
                              │ http://127.0.0.1:8000/api
                              ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║                         CLAUDIYA.AI SYSTEM                                    ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────┐        ║
║  │  MEMBER 6 — API LAYER (FastAPI + Uvicorn)                        │        ║
║  │  ├── CORS middleware (all origins in dev)                        │        ║
║  │  ├── Rate limiting: 30 req/min per API key (in-memory sliding)   │        ║
║  │  ├── REST routes: /api/score, /api/transactions, /api/stats      │        ║
║  │  ├── Auth routes: /api/auth/login, /register, /refresh, /me     │        ║
║  │  ├── WebSocket: /api/ws/dashboard, /ws/transactions, /ws/alerts │        ║
║  │  ├── JWT auth (access 30m + refresh 7d) + API key auth          │        ║
║  │  └── Passes to Orchestrator (v1 legacy or v2 pipeline)           │        ║
║  └────────────────────────────┬─────────────────────────────────────┘        ║
║                               │                                             ║
║  ┌────────────────────────────▼─────────────────────────────────────┐        ║
║  │  MEMBER 2 — ORCHESTRATOR                                         │        ║
║  │  ├── V1 Legacy: score_transaction() in orchestrator/             │        ║
║  │  │   └── Sequential fast_path or parallel LLM agents + fallback  │        ║
║  │  └── V2 Pipeline: RiskOrchestrator in orchestration/             │        ║
║  │      ├── AgentCoordinator with FAST/REASONING/HYBRID modes       │        ║
║  │      ├── CompositeScorer (WeightedScorer / MaxScorer / Ensemble) │        ║
║  │      └── ScoringPipeline (6-stage: Init → Agents → Score →      │        ║
║  │          Guardrail → Persist → Complete)                         │        ║
║  └────────────────────────────┬─────────────────────────────────────┘        ║
║                               │ Parallel execution via asyncio.gather()       ║
║          ┌────────────────────┼────────────┬──────────────┬──────────┐        ║
║          ▼                    ▼            ▼              ▼          ▼        ║
║  ┌───────────────┐  ┌───────────────┐  ┌──────────┐ ┌──────────┐ ┌─────────┐ ║
║  │  MEMBER 5     │  │  MEMBER 4     │  │ MEMBER 5│ │ MEMBER 3│ │ MEMBER 4│ ║
║  │  Device Agent │  │  Behavior     │  │ Network │ │ Trans-   │ │ Behav.  │ ║
║  │               │  │  Agent        │  │ Agent   │ │ action   │ │ Bio     │ ║
║  │  Fingerprint  │  │  Session tele.│  │ Fraud   │ │ Agent    │ │ Agent   │ ║
║  │  IP geo check │  │  Velocity     │  │ Graph   │ │ Hard     │ │ Keystr. │ ║
║  │  Proxy/VPN    │  │  Cart anomaly │  │ COD     │ │ Rules    │ │ Mouse   │ ║
║  │  UA consist.  │  │  COD refusal  │  │ Density │ │ Hard     │ │ Profile │ ║
║  │               │  │               │  │         │ │ Rules +  │ │         │ ║
║  │               │  │               │  │         │ │ XGBoost  │ │         │ ║
║  │               │  │               │  │         │ │ ML +     │ │         │ ║
║  │               │  │               │  │         │ │ SHAP     │ │         │ ║
║  │               │  │               │  │         │ │ (SQL DB  │ │         │ ║
║  │               │  │               │  │         │ │ Vel.)    │ │         │ ║
║  └───────┬───────┘  └───────┬───────┘  └────┬─────┘ └────┬─────┘ └────┬────┘ ║
║          └──────────────────┴───────────────┴────────────┴────────────┘      ║
║                                             │                                 ║
║  ┌──────────────────────────────────────────▼───────────────────────────┐    ║
║  │  MEMBER 2 — COMPOSITE SCORING ENGINE                                 │    ║
║  │  ├── Weighted: device*0.20 + behavior*0.25 + network*0.25 +          │    ║
║  │  │            transaction*0.15 + behavioral_bio*0.15                  │    ║
║  │  ├── Max: max(all agent scores)                                      │    ║
║  │  └── Ensemble: Weighted*0.7 + Max*0.3                                │    ║
║  └──────────────────────────────────┬────────────────────────────────────┘    ║
║                                     │                                         ║
║  ┌──────────────────────────────────▼────────────────────────────────────┐    ║
║  │  MEMBER 7 — GUARDRAIL & COMPLIANCE                                    │    ║
║  │  ├── ComplianceGuardrailAgent (OpenAI Agents SDK LLM validation)      │    ║
║  │  ├── ValidationService (output validation, bias detection, compliance) │    ║
║  │  ├── apply_guardrails() (decision thresholds, fraud ring escalation)   │    ║
║  │  ├── compute_reason_codes() (max 8 codes from agent scores > 20)      │    ║
║  │  ├── fairness check (no raw location-based decline)                   │    ║
║  │  └── Audit log entry (immutable, insert-only)                         │    ║
║  └──────────────────────────────────┬────────────────────────────────────┘    ║
║                                     │                                         ║
║  ┌──────────────────────────────────▼────────────────────────────────────┐    ║
║  │  DATA LAYER (Members 6 + 7)                                           │    ║
║  │  ├── SQLite (dev) / PostgreSQL (prod) — SQLAlchemy async ORM          │    ║
║  │  │   ├── transactions — all scoring requests and decisions            │    ║
║  │  │   ├── audit_log — immutable decision trail                         │    ║
║  │  │   └── users — dashboard login accounts with bcrypt hashes          │    ║
║  │  └── Redis (optional, graceful fallback) — velocity state, rate       │    ║
║  │      limiting, WebSocket pub/sub, caching                             │    ║
║  └───────────────────────────────────────────────────────────────────────┘    ║
║                                                                              ║
║  ┌───────────────────────────────────────────────────────────────────────┐    ║
║  │  MEMBER 7 — INFRASTRUCTURE                                            │    ║
║  │  Docker, Railway deployment, Grafana + Prometheus monitoring          │    ║
║  └───────────────────────────────────────────────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

-----

## 4. The Complete Transaction Flow — From Pay Button to Decision

This is the most important section of this document. It traces every single thing that happens, in order, from the moment a customer clicks Pay to the moment the merchant receives a fraud decision and acts on it.

-----

### Phase 1: Customer Initiates Checkout

**What happens before anything reaches Claudiya.ai:**

A customer is on a merchant's e-commerce website — say, an online electronics store. They have added items to their cart and navigated to the checkout page. They are entering their payment details.

What the customer does not know is that the merchant has integrated Claudiya.ai's API into their checkout backend. When the customer finishes filling in their details and clicks "Pay Now," the merchant's frontend captures the order details — items, amounts, shipping address, billing information, and customer identity — and submits them to the merchant's own backend server.

The merchant's backend is responsible for composing the fraud analysis request. This is where the integration happens. The merchant's code packages the transaction data into a JSON payload and sends it to Claudiya.ai's API endpoint.

**What data is collected at this stage:**

The merchant captures the customer's IP address from the HTTP request headers, the device fingerprint from browser-side JavaScript (if the merchant has implemented it), the user-agent string from the browser, the session duration (how long the customer spent on the checkout page), the billing and shipping addresses, the payment method (card, COD, or wallet), the transaction amount and currency, and the customer's user ID in the merchant's system.

**Who is responsible:** This is the merchant's own integration code. Claudiya.ai provides documentation on the exact request format.

-----

### Phase 2: Merchant Backend Calls Claudiya.ai

**What the merchant's backend does:**

The merchant's backend server receives the order from the frontend. Before the merchant processes the payment with their payment provider (Stripe, PayPal, etc.), they call Claudiya.ai's fraud analysis API. This is the critical integration point. The merchant's backend composes an API request that includes:

The transaction data — the amount, the currency, the payment method (card, cod, or wallet), the device fingerprint, the customer's IP address, the phone number, the shipping address, the user-agent string, and the session duration in seconds.

The customer context — the customer's user ID in the merchant's system, the order ID, and the timestamp of the transaction.

This entire payload is sent to Claudiya.ai as an HTTPS POST request to `/api/score`. If the merchant wants the LLM reasoning path for detailed natural-language explanations, they add `?reasoning=true` to the URL. If they want to use the v2 pipeline, they add `?v2=true`.

**Who is responsible:** This is the merchant's own code. Claudiya.ai provides API documentation and expects a `TransactionIn` schema with all required fields.

-----

### Phase 3: API Authentication & Validation

**What happens inside Claudiya.ai when the request arrives:**

The request hits Member 6's FastAPI application — the main API layer running on Uvicorn.

The first thing that happens is CORS header processing. The CORS middleware allows requests from all origins during development (configurable for production).

The second thing is rate limiting. Member 6's route handler checks an in-memory rate limit store (keyed by API key or a default key). It checks whether the requesting client has made more than 30 requests in the last 60 seconds using a sliding window algorithm. If the limit is exceeded, a 429 Too Many Requests response is returned immediately. The fraud analysis pipeline never starts.

The third thing is schema validation. Pydantic models validate that every required field is present and correctly typed. The `TransactionIn` schema requires `order_id`, `customer_id`, `amount`, `payment_method`, `device_fingerprint`, `ip_address`, `phone_number`, `shipping_address`, `user_agent`, and `session_duration_seconds`. All must be provided with correct types. If the merchant sent a malformed request, a 422 Unprocessable Entity response is returned immediately.

Optionally, if the request includes a valid JWT Bearer token, the authenticated user is attached to the request context for dashboard-driven API calls. For server-to-server scoring, authentication is optional — the endpoint works with or without a user context.

If all checks pass, the request proceeds to the orchestrator.

**Who is responsible:** Member 6 (rate limiter, request validation, route handler).

-----

### Phase 4: Orchestrator Fires All Agents

**What the orchestrator does:**

Member 6's route handler passes the validated request to the scoring pipeline. The route supports two code paths controlled by the `v2` query parameter:

**V1 Legacy Path (default):**

The route calls `score_transaction()` from `app.orchestrator.orchestrator`. This is the original scoring implementation. If `use_reasoning` is true, it runs all five agents with their LLM-based OpenAI Agents SDK implementations in parallel using `_run_agent_with_fallback()` — each agent is given a 30-second timeout, and on any exception, the system falls back to the deterministic fast path function for that agent. If `use_reasoning` is false (fast path), all five `fast_path_*` functions run sequentially.

**V2 Pipeline Path (`?v2=true`):**

The route creates a `RiskOrchestrator` instance with the specified scoring strategy (weighted, max, or ensemble). The `RiskOrchestrator` creates a `RiskEngine` which builds a `ScoringPipeline` — a 6-stage pipeline:

1. **INIT**: Gets or creates a Transaction record in the database from the `TransactionIn` input
2. **AGENT_EXECUTION**: The `AgentCoordinator` runs all five agents. In FAST mode, it calls all five `fast_path_*` functions in parallel via `asyncio.gather()`. In REASONING mode, it runs all five LLM-based agents in parallel via `_run_agent_with_fallback()`. In HYBRID mode, it runs fast path first, identifies agents with scores above 30, and re-runs only those through LLM reasoning.
3. **COMPOSITE_SCORING**: The selected `CompositeScorer` (WeightedScorer, MaxScorer, or EnsembleScorer) combines all five agent results into a single risk score and confidence value.
4. **GUARDRAIL**: Computes reason codes from agent scores above 20, applies decision thresholds, runs fraud ring escalation, and performs fairness checks.
5. **PERSIST**: Updates the Transaction record in the database and creates an AuditLog entry.
6. **COMPLETE**: Returns the final `TransactionDecision`.

The orchestrator also starts a timer to track total processing time, which is included in the final response as `latency_ms`.

**Who is responsible:** Member 2 (orchestrator, scoring pipeline, composite scoring).

-----

### Phase 5: Device Agent Runs

**What Member 5's device agent does in parallel:**

The device agent receives the transaction payload. Its job is to analyze the device and network context of the request — is this device known? Is the IP address trustworthy? Does the user-agent match historical patterns?

It runs four independent checks in its fast path implementation:

**Device fingerprint reuse check:** It queries the database for transactions in the last 30 days that share the same `device_fingerprint`. It counts how many distinct customers have used this device (excluding the current customer) and how many total transactions have been made from it. A device shared across many customers is suspicious — it suggests a shared fraud device, not a personal computer.

**IP geolocation mismatch check:** It performs a mock geolocation lookup on the IP address. It determines the geographic region of the IP (e.g., "Northeast" for IPs starting with certain prefixes, "West" for others, default "Unknown"). It compares this against the shipping address's state to compute a mismatch score. A mismatch of 0.0 means the IP region matches the shipping address state. A mismatch of 0.7 means a complete mismatch — the buyer appears to be in one region but shipping to a completely different one.

**Proxy/VPN detection check:** It checks whether the IP address belongs to a known proxy or VPN range. IPs starting with `10.` (private range) or `203.0.113.` (documentation/test range) are flagged as proxies. If a proxy is detected, a confidence of 0.9 is assigned. If not, confidence is 0.1.

**User-agent consistency check:** It queries the customer's last 5 transactions and compares their user-agent strings. If this transaction uses a different user-agent than previous ones, it indicates possible account takeover — the real customer's browser signature has changed.

Each check produces a signal value (a numerical measurement). The device agent converts each signal to a score (0–100) using `score_from_signal()`, which applies piecewise linear interpolation based on the thresholds defined in the policy configuration. If any signal score exceeds 20, its explanation is added to the evidence list. The final device score is the average of all signal scores, with a confidence of 0.85.

In the reasoning path, these four checks are wrapped as OpenAI function tools that the LLM-based `device_agent` (gpt-4o-mini) can call. The LLM interprets the results and produces a natural-language explanation alongside the structured score.

**Who is responsible:** Member 5 (`app/agents/device_agent.py`).

-----

### Phase 6: Behavioral Agent Runs

**What Member 4's behavioral agent does in parallel:**

The behavioral agent analyzes the transaction behavior — how the customer interacts with the checkout process, their ordering velocity, and their historical payment patterns.

It runs four independent checks in its fast path implementation:

**Order velocity check:** It queries the database for orders in the last 1 hour and last 24 hours that share the same `customer_id` or `phone_number`. It counts how many orders were placed in each window. A customer placing many orders in a short time is suspicious — it could indicate a fraudster rapidly testing stolen cards or making multiple fraudulent purchases before detection.

**Session anomaly check:** It compares the `session_duration_seconds` (how long the customer spent on the checkout page) against an expected minimum duration. The expected minimum is calculated as `max(30 seconds, amount * 0.5)`. For example, a $200 transaction expects at least 100 seconds on the checkout page. A session duration significantly shorter than expected produces a high anomaly score (up to 0.9). Sessions under 30 seconds are always flagged regardless of amount.

**Cart value anomaly check:** It queries the customer's order history and computes the average transaction amount. The current transaction's amount is compared to this average — the deviation ratio measures how far the current amount deviates from the customer's normal spending pattern. A customer who usually buys $50 items suddenly buying a $500 item is a signal worth investigating.

**COD refusal rate check:** It queries the customer's COD (Cash on Delivery) transaction history. It counts total COD orders and simulates a refusal count (random between 0 and half of COD orders). A high COD refusal rate is a strong friendly fraud signal — the customer receives the goods but refuses to pay. The special customer ID `FRIENDLY_REPEAT_001` is hardcoded to produce a high refusal rate for testing purposes.

Each signal is scored using `score_from_signal()` with behavioral thresholds. The final behavior score is the average, with confidence 0.85.

In the reasoning path, the `behavior_agent` (gpt-4o-mini) uses all four checks as function tools and produces structured output with natural-language explanations.

**Who is responsible:** Member 4 (`app/agents/behavior_agent.py`).

-----

### Phase 7: Network Agent Runs

**What Member 5's network agent does in parallel:**

The network agent analyzes the transaction from a graph perspective — it builds a fraud network using NetworkX to detect connections between seemingly unrelated transactions.

It runs two checks in its fast path implementation:

**Fraud graph construction:** It fetches all transactions from the last 60 days from the database. Using NetworkX, it builds a graph where nodes represent customers, devices, phone numbers, and shipping addresses. Edges connect customers to the entities they have used (a customer node is connected to the device nodes, phone nodes, and address nodes associated with their transactions).

For the current transaction's customer, the agent finds the connected component in this graph — all customers, devices, phones, and addresses that are reachable through shared entities. If the component contains more than one customer sharing the same device, phone, or address, this is a fraud ring signal. The agent records the size of the component and collects the order IDs of all linked transactions as evidence.

**COD address density check:** It computes how many COD (Cash on Delivery) orders share the current shipping address versus a system-wide baseline (total COD orders divided by 100). A density ratio above 2.0 is considered elevated — it means this address receives significantly more COD orders than the average address, which is a pattern consistent with fraud rings using a common drop address.

The network score combines the component size signal and the COD density signal. If the component contains linked customers, the linked order IDs are carried as evidence to the final decision.

In the reasoning path, the `network_agent` (gpt-4o-mini) uses `build_fraud_graph` and `check_cod_address_density` as function tools.

**Who is responsible:** Member 5 (`app/agents/network_agent.py`).

-----

### Phase 8: Transaction Agent Runs

**What Member 3's transaction agent does in parallel:**

The transaction agent is the most sophisticated of the five agents. It uses a **two-layer hybrid architecture** — Layer 1 is a hard rule engine that catches definitive fraud instantly by blocking with score=100 and skipping the ML layer entirely, and Layer 2 is an XGBoost machine learning model that scores everything else with nuance and explainability.

The two layers run sequentially: Layer 1 executes all four hard rule checks first. If any hard rule fires, the agent returns score=100 immediately and the ML model is never called. If no hard rule fires, the agent proceeds to Layer 2 where velocity features are computed via SQL database queries, BIN data is fetched, a 25-feature vector is assembled, and XGBoost inference produces a fraud probability with SHAP explanation.

**Crucially, the transaction agent reads three enriched fields from the shared payload:** `ip_country`, `is_vpn`, and `is_proxy` — these are set by Member 5's device agent and used for BIN country mismatch analysis and as ML features.

All velocity tracking throughout both layers uses **SQLAlchemy queries against the `transactions` table** — not Redis. The core helper `_count_orders(**filters)` runs parameterized SQL queries with timestamp-based time windows (1h, 6h, 24h, 7d) across four dimensions (customer, device, IP, phone). This avoids the operational complexity of maintaining Redis while keeping all state in the primary database.

---

**Layer 1 — Hard Rule Engine (Deterministic, Sub-Millisecond):**

Layer 1 implements four definitive fraud patterns. Each of these patterns represents a scenario where the fraud signal is unambiguous — there is no legitimate explanation for the pattern. If any rule fires, the agent returns `score=100`, `hard_blocked=true`, and the ML model is never invoked. The response time for a hard block is typically 5–10ms.

**Hard Rule 1 — Card Testing Attack Detection:**

This rule detects the most common automated fraud pattern: a fraudster tests stolen credit cards with micro-transactions to verify which ones are still active, then uses a working card for a large purchase.

The rule tracks all transaction amounts from a specific device fingerprint in the last 7 days using a SQLAlchemy query (`_get_recent_txns(device_fingerprint=...)`). A micro-transaction threshold is defined at $20.00. Transactions under this threshold are counted as potential card testing attempts. If there are 5 or more such micro-transactions from the same device, the `is_card_testing_pattern` flag is set to true.

The micro-transactions themselves are tracked but not blocked — the fraudster is allowed to test cards freely while the system accumulates evidence. If the pattern is detected (5+ small transactions all under $20 from the same device), this hard rule fires at the Layer 2 stage via the ML model, while in Layer 1 the extreme velocity rule catches the most aggressive cases.

**Hard Rule 2 — Extreme Velocity Detection:**

This rule detects an automated carding script running at high speed. It tracks how many orders have been placed across any dimension (customer, device, IP, phone) in the last 1 hour using the `_count_orders()` SQL helper.

The rule checks `max_1h` — the maximum order count across all four dimensions. If `max_1h >= 10`, hardcoded logic in `compute_velocity_score()` assigns a score of 85 and escalates. This is complemented by the `score_from_signal()` path via the `velocity_burst_1h` thresholds defined in `policy.py`.

The velocity data is also used by the Layer 2 ML model as numeric features — the soft thresholds (3 in 1h) feed into XGBoost, while the hard threshold (10+ in 1h) can trigger a score of 100 in the guardrail layer.

**Hard Rule 3 — Freight Forwarder Address Detection:**

A freight forwarder (also called a reshipping service) is a physical warehouse that accepts deliveries and re-ships them to another international address. Fraudsters use them to obscure the true destination of stolen goods. For example, a fraudster in Nigeria steals a UK card and ships $500 of electronics to a freight forwarder in Miami — the Miami address looks legitimate, but the goods are re-shipped to Nigeria.

This rule uses three detection layers, all entirely self-contained with no external API required, all using SQL database queries:

**Layer A — Keyword matching on the address string:** The shipping address is checked against known freight forwarder keywords: "freight", "forwarder", "forwarding", "reshipping", "pmb", "mailbox", "mailboxes etc", "the ups store", "ups store", "pak mail", "mailstop". These businesses describe themselves consistently in their registered addresses, and fraudsters copy the address exactly from the freight forwarder's website.

**Layer B — Static ZIP code list:** The shipping ZIP code is checked against a known set of freight forwarder hub ZIPs: Miami, FL (33166, 33126, 33172 — the single largest freight forwarding hub in the US), New York (10001, 11101), Los Angeles (90220), Houston (77032), and Delaware (19720). A ZIP in this list is a definitive freight forwarder signal. This is maintained as a Python `set` for O(1) lookup.

**Layer C — Chargeback-derived hotlist:** Every time a chargeback is traced to a shipping address not in the static list, that address is added to a `freight_forwarder_addresses` PostgreSQL table. Over time, this hotlist becomes the most accurate detection layer — it reflects the platform's actual fraud patterns, not a generic industry list. Queried via SQL on each transaction.

If any of these three layers produces a match, the hard rule fires and the transaction is blocked at score=100.

**Hard Rule 4 — CVV Missing + AVS No-Match Combined:**

This rule fires when a transaction has both CVV missing AND the AVS (Address Verification Service) result is "N" (no match — neither street nor ZIP matches the card's records).

The combination is the exact signature of a stolen card data dump. When card numbers are stolen in bulk data breaches, the dump typically includes only the card number and expiry date — not the CVV. The fraudster has the card number but not the physical card, so they cannot provide the CVV. The billing address is also completely wrong because the dump did not include it — the fraudster guesses or uses a fake address.

Either signal alone (CVV missing OR AVS mismatch) is not definitive — legitimate reasons exist for each. But both together is near-certain proof of stolen card data being used without the physical card present.

---

**Layer 2 — XGBoost ML Scoring Engine (Runs Only If No Hard Block Fired):**

If no hard rule fires, the agent proceeds to the ML layer. This layer handles the remaining 95% of transactions with nuanced scoring.

**Step 1 — BIN Lookup:**

Before computing features, the agent performs a BIN (Bank Identification Number) lookup on the first 6 digits of the card number. The BIN reveals: the issuing country of the card (for bin_country_match analysis), the card type (credit, debit, prepaid, gift, or virtual), and the issuing bank name.

The agent uses a self-hosted BIN database in PostgreSQL (for production) — queried via SQL with a `bin_prefix` index — with an external API fallback (for development). If the lookup fails or times out after 2 seconds, neutral default values are used and a `bin_lookup_failed` flag is added.

**Step 2 — Velocity Feature Computation via SQL:**

The agent computes velocity counts across three dimensions using SQL queries on the `transactions` table, not Redis. The core function `_count_orders()` runs parameterized `SELECT COUNT(*) FROM transactions WHERE {column} = {value} AND timestamp >= {window_start}` queries:

- `card_velocity_count`: How many times this specific card (identified by BIN + last4) has been used in the last 10 minutes, queried via SQL with a 10-minute timedelta window
- `ip_velocity_count`: How many transactions have originated from this IP in the last 5 minutes, queried via SQL with a 5-minute timedelta window
- `user_velocity_count`: How many orders this user account has placed in the last 1 hour, queried via SQL with a 60-minute timedelta window

These counts are NOT hard block signals at this layer — they become numeric features in the ML feature vector. The ML model decides how much weight to assign to each count based on the full context of the transaction. The same SQL-based `_count_orders()` helper also computes 6h, 24h, and 7d windows for additional context.

**Step 3 — 25-Feature Vector Assembly:**

The feature engineering step assembles all available data into a 25-feature vector that the XGBoost model expects. The features are grouped into 9 categories:

*Group 1 — Amount Features (2 features):*
Feature 0: `amount` — raw transaction amount in base currency
Feature 1: `amount_log` — log(1 + amount), compresses the right-skewed distribution so large transactions don't dominate the model

*Group 2 — Temporal Features (3 features):*
Feature 2: `hour_of_day` — UTC hour 0–23. Fraud bots often operate in early morning hours (1am–5am) when monitoring is lighter.
Feature 3: `day_of_week` — Monday 0 through Sunday 6. Different fraud types peak on different days.
Feature 4: `is_weekend` — binary 1 if Saturday or Sunday. Makes the weekend pattern explicit for the model.

*Group 3 — Velocity Features (3 features, sourced from SQL):*
Feature 5: `card_velocity_count` — from SQL query on `transactions` table, 10-minute window
Feature 6: `ip_velocity_count` — from SQL query on `transactions` table, 5-minute window
Feature 7: `user_velocity_count` — from SQL query on `transactions` table, 60-minute window

*Group 4 — Card Verification Features (2 features):*
Feature 8: `avs_code_encoded` — AVS result encoded ordinally: Y=0 (full match), A/Z/U=1-2 (partial), N=3 (no match)
Feature 9: `cvv_missing` — binary 1 if CVV was not provided

*Group 5 — Address Features (3 features):*
Feature 10: `billing_shipping_country_match` — binary 1 if billing country equals shipping country
Feature 11: `billing_shipping_zip_match` — binary 1 if billing ZIP equals shipping ZIP
Feature 12: `is_freight_forwarder` — binary 1 if the shipping address matched a freight forwarder near-match pattern

*Group 6 — BIN and Device Features (4 features):*
Feature 13: `bin_country_match` — 3-valued: 1.0 if BIN country matches IP country, 0.0 if mismatch, 0.5 if IP is VPN (uncertain)
Feature 14: `is_vpn` — binary from Member 5's device agent
Feature 15: `is_proxy` — binary from Member 5's device agent
Feature 16: `is_prepaid_card` — binary from BIN lookup, prepaid cards are anonymous and preferred by fraudsters

*Group 7 — Merchant Feature (1 feature):*
Feature 17: `merchant_risk_multiplier` — numeric risk multiplier for the merchant's product category. Gift cards = 1.8, crypto = 1.7, electronics = 1.4, clothing = 1.0, groceries = 0.6, utilities = 0.4.

*Group 8 — User History Features (5 features, sourced from SQL):*
Feature 18: `account_age_days` — days since account creation, queried via SQL from `users` table
Feature 19: `chargeback_count_90d` — number of chargebacks filed by this user in the last 90 days, queried via SQL from `chargebacks` table
Feature 20: `return_rate` — return_count / total_orders, queried via SQL from `users` table
Feature 21: `total_orders` — lifetime order count, queried via SQL from `users` table
Feature 22: `is_new_account` — binary 1 if account_age_days < 7

*Group 9 — Behavioral Context Features (2 features):*
Feature 23: `amount_vs_user_avg_ratio` — current amount divided by user's historical average approved amount (last 30 days, queried via SQL)
Feature 24: `is_micro_transaction` — binary 1 if amount is $1.00 or less

The feature vector is always assembled in exact order (position 0 through 24) because XGBoost identifies features by position, not by name. An assertion validates that the vector has exactly 25 features before inference.

**Step 4 — XGBoost Inference:**

The 25-feature vector is passed to a pre-trained XGBoost classifier. XGBoost (eXtreme Gradient Boosting) is an ensemble of decision trees trained sequentially — each new tree corrects the errors of the previous ones. It is the industry standard for tabular fraud detection, used by PayPal, Stripe, Adyen, and Riskified.

The model returns a fraud probability between 0.0 and 1.0. This probability is scaled to a 0–100 score using a non-linear mapping: probabilities below 0.5 map to scores 0–70 (providing finer resolution in the low-risk range), and probabilities above 0.5 map to scores 70–100 (providing finer resolution where precise differentiation matters most).

The model is loaded into memory once at application startup and remains resident for the lifetime of the process. If the model file is not found or fails to load, the agent runs in rule-only mode, returning ml_score=50 and adding the `ml_model_unavailable` flag. Inference runs in a thread pool to avoid blocking the async event loop — typical inference time is 1–3ms on CPU.

**Step 5 — SHAP Explainability:**

After inference, the agent runs a pre-built SHAP TreeExplainer on the same feature vector. SHAP (SHapley Additive ExPlanations) computes the contribution of each feature to the final prediction, producing a per-transaction explanation like:

"card_velocity_count contributed +0.23, merchant_risk_multiplier contributed +0.22, is_vpn contributed +0.19, avs_code_encoded contributed +0.11, amount_vs_user_avg_ratio contributed +0.08."

The top 5 contributing features are returned, each with its feature name, SHAP contribution value (positive means pushed toward fraud), and the raw feature value at the time of inference. This explanation travels with the decision through the guardrail layer and is visible to merchant analysts reviewing flagged transactions.

If the SHAP explainer fails to load or errors during inference, the explanation is returned as null — this is non-critical, the score itself is still valid.

**Step 6 — Soft Flag Computation:**

For transparency, the agent computes soft flags indicating which signals were elevated. These flags do not affect the score (the ML model has already accounted for them as features) but appear in the output for explainability and audit trail purposes.

Soft flags include: card/ip/user velocity elevated (from SQL queries), AVS no-match or partial match, address country mismatch, high-risk merchant category, VPN detected.

**Score Combination Logic:**

The final score returned to the orchestrator follows these rules:

If a hard block fired (Layer 1): final_score = 100, hard_blocked = true, ml_fraud_probability = 0.0, shap_explanation = null. The ML model was never called.

If no hard block fired (Layer 2): final_score = ml_score from XGBoost (0–100). The soft rule signals were already fed as features into the ML model — they are not added on top to avoid double-counting. The ml_fraud_probability and shap_explanation are populated.

If the ML model was unavailable: final_score = 50 (neutral), ml_fraud_probability = 0.5, with the `ml_model_unavailable` flag.

**Model Training Pipeline (Offline):**

The XGBoost model is trained offline — not during API request handling. The training pipeline runs weekly (every Monday at 2 AM UTC via GitHub Actions) and follows this process:

1. Loads labeled transactions from the `fraud_labels` table via SQL — confirmed fraud (label=1 from chargebacks, arriving 30–90 days after transaction) and confirmed legitimate (label=0 from 120-day no-dispute assumption, assigned by nightly batch job)
2. Reconstructs the 25-feature vector for each labeled transaction using the exact same `compute_features()` function used at inference time — this guarantees training-inference consistency. Velocity features are computed via the same SQL queries, not Redis.
3. Trains an XGBoost classifier with parameters optimized for fraud detection: 300 trees, max depth of 6, learning rate of 0.05, scale_pos_weight set to compensate for class imbalance (fraud is ~0.1–1% of transactions)
4. Evaluates using 5-fold stratified cross-validation, targeting AUC-ROC above 0.85
5. Saves the trained model, SHAP TreeExplainer, and metadata to the `models/` directory
6. The next application deployment picks up the new model files

For initial training before the platform has accumulated real chargeback labels, the model is trained on the IEEE-CIS Fraud Detection dataset (590,540 real e-commerce transactions from Vesta Corporation). Seven features that do not exist in the IEEE-CIS dataset (cvv_missing, is_freight_forwarder, is_vpn/proxy details, chargeback history, return rate) are defaulted to 0 — the model learns from the remaining 18 features and improves when retrained on real platform data.

**Velocity state management (SQL-based, not Redis):**

All velocity tracking uses SQLAlchemy queries against the `transactions` table with timestamp-based time windows. The core helper `_count_orders(**filters)` runs a parameterized `SELECT` with a `WHERE` clause filtering by the relevant column and a `timestamp >= window_start` condition. Four time windows are queried per dimension: 1 hour, 6 hours, 24 hours, and 7 days.

The four velocity dimensions — customer_id, device_fingerprint, ip_address, and phone_number — each get their own SQL query per window. The maximum counts across all dimensions (`max_1h`, `max_24h`) are computed server-side after all queries return.

This SQL-based approach avoids the operational complexity of maintaining Redis while providing the same functionality. The `transactions` table is indexed on `customer_id`, `device_fingerprint`, `ip_address`, and `timestamp` for query performance.

**Who is responsible:** Member 3 (`app/agents/transaction_agent.py`, `app/tools/velocity_checker.py`, `app/tools/fraud_patterns.py`, `ml/feature_engineering.py`, `ml/model_trainer.py`, `ml/model_inference.py`, `ml/shap_explainer.py`, `services/bin_lookup.py`).

-----

### Phase 9: Behavioral Bio Agent Runs

**What Member 4's behavioral bio agent does in parallel:**

The behavioral bio agent is a separate agent from the behavior agent above. While the behavior agent focuses on transactional behavior (velocity, session patterns, COD history), the behavioral bio agent focuses on user biometrics and profile analysis — how the user interacts with the system at a finer granularity.

It runs five analysis functions in its fast path implementation:

**Login anomaly analysis:** It examines the customer's login history over the last 30 days. It counts distinct IP addresses used, distinct user-agents, and how frequently the IP has changed. A new customer with no history gets a neutral score of 0. An established customer with more than 5 distinct IPs gets +40. More than 3 distinct IPs gets +20. More than 3 distinct user-agents gets +25. More than 10 IP changes gets +30. If the current user-agent differs from any recent ones, an additional +15 is added.

**Session pattern analysis:** It computes the z-score of the current session duration against the customer's historical average session duration. It also computes the ratio of current amount to duration against the historical average ratio. A z-score with absolute value above 2 adds +30, above 3 adds another +20. An amount-to-duration ratio above 3 times the historical average adds +25. A ratio below 0.3 times the average adds +15.

**Typing biometrics analysis:** Since the system does not have a browser SDK to capture actual keystrokes (unlike the AegisFlow design), this function simulates biometric analysis from available data. It estimates typing speed from the session duration and user-agent characteristics. Sessions under 5 seconds with an amount over $200 suggest automation (+50). Implied typing speeds under 20 wpm suggest a non-human (+25). Implied speeds over 100 wpm suggest automation (+20).

**Mouse behavior analysis:** It analyzes the session duration and device fingerprint for mouse behavior signals. A session under 3 seconds immediately returns a bot-like risk of 60. For longer sessions, it simulates mouse movement analysis — random mouse event counts, path naturalness scoring, and jitter detection. No jitter in movements adds +40. Low path naturalness adds +30. Too few mouse movements add +20. Too many add +15.

**User behavior profile analysis:** It builds a 90-day profile of the customer including their preferred payment methods, typical hours of transaction, number of distinct IPs used, and IP change frequency. From these, it computes a `profile_stability` score: `max(0, 100 - distinct_ips * 10 - ip_changes * 5 - distinct_hours * 3)`. A profile stability below 30 adds a fixed 50 penalty points.

All five analysis scores are combined into a final behavioral intelligence score. If any sub-score exceeds 30, its explanation is added to the evidence list. The final score is capped at 100 and limited to 6 reason codes maximum.

In the reasoning path, the `behavioral_agent` (gpt-4o-mini) uses all five analysis tools to produce structured output.

**Who is responsible:** Member 4 (`app/agents/behavioral_agent.py`, `app/tools/behavior_analysis.py`).

-----

### Phase 10: Composite Scoring

**What happens after all five agents return:**

Member 2's orchestrator now has five results, each containing a score (0–100), a confidence value, an explanation string, and a list of evidence strings.

**Three scoring strategies are available:**

**Weighted scoring (default):** The five scores are combined using hardcoded weights:

| Agent | Weight | Purpose |
|-------|--------|---------|
| Device | 0.20 (20%) | Fingerprint, IP geolocation, proxy/VPN, user-agent |
| Behavior | 0.25 (25%) | Order velocity, session anomaly, cart deviation, COD refusal |
| Network | 0.25 (25%) | Fraud graph analysis, COD address density |
| Transaction | 0.15 (15%) | Card testing, COD ring, friendly fraud, triangulation, velocity |
| Behavioral Bio | 0.15 (15%) | Login anomaly, session patterns, typing, mouse, profile |

The composite risk score is the weighted sum of all five agent scores, clamped to the range [0, 100]. The confidence is calculated as `BASE_CONFIDENCE (0.85) * product(1 - score/200)` across all agents — this means confidence decreases as any agent reports a high score.

**Max scoring:** The composite score is simply the maximum of all five agent scores. This is the most conservative strategy — it trusts the highest-risk signal entirely. Confidence is fixed at `BASE_CONFIDENCE (0.85)`.

**Ensemble scoring:** A weighted combination of the WeightedScorer (70%) and MaxScorer (30%). Both the risk score and confidence are computed as weighted averages of the two constituent scorers. This balances the smoothness of weighted averaging with the conservatism of max scoring.

**Decision mapping:**

The composite score maps to one of three decisions:

| Score | Decision | Meaning |
|-------|----------|---------|
| 0 – 29 | approve | Transaction is clean — proceed with payment |
| 30 – 69 | review | Uncertain — hold for human analyst review |
| 70 – 100 | decline | High risk — reject transaction |

Merchant-specific threshold overrides are not yet implemented but the architecture supports them through the `configs/policies.py` policy configuration system.

**Who is responsible:** Member 2 (`app/orchestration/composite_scorer.py`, `app/orchestrator/policy.py`).

-----

### Phase 11: Guardrail Validation

**What Member 7 does before the decision leaves Claudiya.ai:**

The composite decision passes through Member 7's guardrail layer before it is returned to the merchant. This is the compliance and safety layer — it exists to catch things that may have gone wrong in the pipeline and to enforce absolute rules regardless of score.

**Reason code computation:**

The guardrail calls `compute_reason_codes()` with the three primary agent results (device, behavior, network). For each agent where the score exceeds 20 and the explanation is not a clean message, the explanation is appended as a reason code. If an agent has no explanation but has evidence items, the first three evidence items are used instead. The same logic is then applied to the transaction and behavioral-bio agents. A maximum of 8 reason codes are allowed.

**Decision thresholding (apply_guardrails):**

The guardrail applies the decision threshold rules:

If the composite risk score is below 30, the decision is `approve`. If the risk score is above 70, the decision is `decline`. If the risk score is between 30 and 70 (inclusive), the decision is `review`, and a `guardrail_applied` flag is set to true to indicate that the guardrail made the final decision call, not the raw score.

**Fraud ring escalation:**

If the network agent produced evidence (indicating a fraud ring was detected) AND the guardrail's preliminary decision was `approve`, the guardrail forces the decision to `review`. This ensures that even if the composite score accidentally falls below 30 for a fraud ring transaction, it is never automatically approved — it always goes to human review.

**Fairness check:**

The guardrail performs a documented fairness check (`_check_fairness()`). The policy states that raw location should never be used as a decline signal. Location-based risk must only influence the decision through indirect signals — the network agent's COD address density and the device agent's IP geolocation mismatch. This prevents the system from unfairly penalizing customers in regions where COD is more common.

**Validation service:**

Before the decision leaves the system, the `ValidationService` performs additional checks:

- **Output validation**: Ensures all required fields are present, risk score is within [0, 100], confidence is within [0, 1], no agent scores are negative, reason codes do not exceed 8, and the decision is consistent with the score (approve must have risk < 30, decline must have risk > 70).

- **Confidence validation**: Ensures the confidence meets minimum thresholds for each decision type — approve requires confidence >= 0.75 and risk <= 30, review requires confidence >= 0.60 and risk <= 70, decline requires confidence >= 0.80 and risk >= 70.

- **Compliance checks**: Runs three compliance checks — GDPR requires at least 1 reason code for explainability, AML flags transactions of $10,000 or more for review or decline, and KYC marks review decisions as needing customer verification.

- **Bias detection**: Compares mean risk scores across groups (by region, by payment method) against a maximum disparity threshold. If the disparity exceeds 0.15 for region or 0.10 for payment method (COD vs. card), a bias flag is raised.

- **Human review escalation**: Checks if any escalation trigger is active — confidence below 0.60, borderline score in [25, 35], confidence validation failure, or any bias check failure. If triggered, the decision is escalated to human review.

**Compliance guardrail agent (LLM):**

For complex or borderline cases, the `compliance_guardrail_agent` (gpt-4o-mini) is invoked. This LLM-based agent validates the output for safe, fair, and compliant decision-making. It enforces rules including: never approve if risk >= 30, never decline if risk <= 70, escalate if confidence < 0.60 or risk in [25, 35], and escalate if bias checks fail. The guardrail agent produces a `ComplianceCheckResult` with a passed/failed status, an override decision if needed, and a list of issues.

**Audit log entry:**

Every single transaction that passes through Claudiya.ai — approved, declined, or reviewed — gets a permanent, immutable record written to the `audit_log` table. This table is insert-only: no updates and no deletes are ever performed on it. Each audit entry records the `order_id`, `event_type` (either "score" or "override"), the previous decision (if applicable), the new decision, and a JSON details payload containing the full decision context. This creates a complete, permanent paper trail of every fraud decision ever made by the system.

**Who is responsible:** Member 7 (`app/agents/compliance_guardrail.py`, `app/guardrail/guardrail.py`, `app/services/validation_service.py`, `app/configs/policies.py`).

-----

### Phase 12: Response Returned to Merchant

**What Claudiya.ai sends back:**

After the guardrail validation, Member 6's API route receives the validated decision and composes the final response. The total elapsed time from receiving the request to sending this response should be under 200 milliseconds for fast-path transactions.

The response contains:

- `order_id` — echoed back so the merchant can match this response to their original request
- `decision` — one of: `approve`, `review`, `decline`
- `risk_score` — the composite fraud score, 0–100
- `confidence` — the confidence level in the decision, 0–1
- `agent_scores` — a dictionary of per-agent scores (device, behavior, network, transaction, behavioral)
- `reason_codes` — a list of the fraud signals that were detected (max 8)
- `latency_ms` — how long the analysis took in milliseconds
- `scoring_path` — which execution path was used (fast, reasoning, or hybrid)

While composing this response, Member 6 also kicks off two background tasks that do not block the response:

The fraud decision is persisted to the database (the Transaction record is updated with the final decision, risk score, and latency). This happens after the response has already been sent — the merchant does not wait for this write.

A push notification is sent to all active WebSocket connections via `notify_new_transaction()`. This is what makes the dashboard update in real time. If the risk score exceeds 50, an additional high-risk alert is broadcast to the alerts WebSocket channel.

**Who is responsible:** Member 6 (`app/api/routes.py`).

-----

### Phase 13: Merchant Acts on Decision

**What happens on the merchant side after receiving the response:**

The merchant's backend server receives the JSON response from Claudiya.ai and immediately acts on the `decision` field:

If `decision == "approve"`, the merchant proceeds to call their payment provider to actually charge the card. The transaction completes and the customer sees a success confirmation.

If `decision == "decline"`, the merchant rejects the transaction entirely. The customer sees a generic error message. The merchant never reveals that fraud detection was the reason — this is intentional. Fraudsters who receive specific error messages learn what patterns triggered detection and adjust their approach.

If `decision == "review"`, the merchant holds the transaction in a pending state. A fraud analyst on the merchant's team reviews the flagged signals (visible in the Claudiya.ai dashboard) and makes a manual decision. The customer is typically told that their order is being processed.

**Who is responsible:** This is the merchant's own code and business logic.

-----

### Phase 14: Dashboard Updated in Real Time

**What happens in the merchant's dashboard simultaneously:**

While the merchant's backend is acting on the fraud decision, the Claudiya.ai dashboard is updating in real time. Member 6's WebSocket system has already pushed the transaction decision to all active dashboard sessions.

The dashboard shows the merchant's fraud analyst team a live feed of every transaction being processed, displayed in a threat feed with severity coding. Approved transactions appear in green, declined in red, and review in yellow. Each entry shows the transaction amount, risk score, and agent flags.

Key dashboard components update simultaneously:

**StatCard components** display live KPI metrics — total events per second, blocked transaction count, average decision time, and precision rate. Each card shows a delta indicator (positive or negative trend) and includes a shimmer bar animation.

**RiskChart component** displays a stacked area chart (Recharts) showing the risk contribution of all three primary agents (orchestrator, behavior, device) over the last 24-hour window, giving analysts a visual overview of risk trends.

**AgentProgress component** shows an animated pipeline visualization with three parallel progress bars (one per primary agent), each displaying its real-time score, latency, and scored count. The bars animate through stages (fingerprinting, telemetry, graph analysis, etc.) to give analysts visibility into what each agent is doing.

**ThreatFeed component** displays a live scrolling list of real transactions with severity coding. Each entry is shown as it arrives, with an animated entrance. Analysts can click any entry to see more details.

**Agent detail pages** at `/agents/orchestrator`, `/agents/behavior`, and `/agents/device` provide deep dives into each agent's performance — showing per-agent metrics (score, latency, count, weight), guardrail compliance results, and agent-specific visualizations (network graph for orchestrator, behavior analysis for behavior agent, device intelligence for device agent).

**Admin panel** at `/admin` shows agent health (online/offline status, scores, latency for all 5 agents), global guardrail toggle switches, data generation controls (generate clean or fraud transactions to test the pipeline), and recent transaction activity.

**Agent progress page** at `/progress` provides full pipeline observability with an audit event timeline showing every decision made, the agent that produced it, the score, and the timestamp.

**Who is responsible:** Member 6 (WebSocket routes, API endpoints), Member 2 (frontend).

-----

## 5. Member 1 — Team Lead / AI Architect

### Role Summary

Member 1 is responsible for everything that makes the other seven members' work possible and coherent. This is not a coding role in the traditional sense — it is a coordination, architecture, and integration role.

### Core Responsibilities

**Repository setup and maintenance.** Member 1 creates and manages the GitHub repository. This includes defining the branch strategy, configuring branch protection rules (no direct pushes to main, all PRs must pass CI), setting up the folder structure that every other member's code will live in, and creating the shared configuration files that every member imports.

**Shared configuration.** Member 1 writes the `app/core/config.py` file that defines how all environment variables are read. Every member who needs the database URL, Redis URL, OpenAI API key, JWT secret, or any other setting reads it from the centralized `Settings` class — never hardcoded. The `get_settings()` singleton ensures consistent configuration across the application.

**Application entry point.** Member 1 writes `app/api/main.py` — the file that starts the FastAPI application. This file is responsible for the lifespan handler which initializes all shared resources at startup: creating the database tables (`init_db()`), seeding synthetic data if the database is empty (`seed_database()`), and closing the Redis connection on shutdown. It also configures CORS middleware, mounts all routers (API, auth, WebSocket), and sets up the OpenAI Agents SDK (disables tracing, sets default API).

**Shared dependencies.** Member 1 writes `app/core/security.py` (password hashing with bcrypt, JWT creation and verification with jose) and `app/core/dependencies.py` (FastAPI dependency injection for user authentication — `get_current_user`, `require_user`, `optional_user`, and `ws_auth` for WebSocket authentication).

**Pull request review and merging.** Every PR from every team member goes through Member 1 before it merges into main. Member 1 checks that CI passes, reviews for obvious errors, and ensures the code matches the agreed interfaces.

**Final integration and testing.** When all members have merged their code, Member 1 runs end-to-end integration tests to verify that the full pipeline works together as described in Section 4 of this document.

**Presentation.** Member 1 presents the full system architecture during the product demo.

### Files Member 1 Owns

`app/api/main.py`, `app/core/config.py`, `app/core/__init__.py`, `app/core/security.py`, `app/core/dependencies.py`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, `opencode.json`.

-----

## 6. Member 2 — Orchestrator Engineer

### Role Summary

Member 2 builds the brain of Claudiya.ai. The orchestrator is the central coordination layer that receives every transaction analysis request and directs the five specialist agents to analyze it. It is responsible for parallel execution, combining results, composite scoring, and producing the final decision. Member 2 maintains both the V1 legacy orchestrator and the V2 pipeline architecture. Member 2 also builds the frontend dashboard — a TanStack Start + Vite React application with Tailwind v4, shadcn/ui, and Framer Motion animations.

### Core Responsibilities

**V1 legacy orchestrator.** Member 2 maintains `score_transaction()` in `app/orchestrator/orchestrator.py`. This function gets or creates a Transaction record in the database, runs all five agents (either via fast path sequentially or via LLM in parallel with fallback), computes the weighted score, applies guardrails, persists the result, and returns the `TransactionDecision`. It is the default scoring path used by the API when `v2` is not specified.

**V2 pipeline architecture.** Member 2 builds the modern `ScoringPipeline` in `app/orchestration/pipeline.py` — a 6-stage pipeline (INIT, AGENT_EXECUTION, COMPOSITE_SCORING, GUARDRAIL, PERSIST, COMPLETE) with detailed stage timing that enables operators to see exactly where time is spent.

**Agent coordinator.** Member 2 builds the `AgentCoordinator` class in `app/orchestration/coordinator.py` that supports three execution modes: FAST (all fast_path functions in parallel via `asyncio.gather()`), REASONING (all LLM agents in parallel with fallback), and HYBRID (fast first, then LLM reasoning for high-risk agents). Each agent invocation has a configurable timeout (default 30 seconds) and falls back to the fast path on any failure.

**Composite scoring engine.** Member 2 builds three scoring strategies in `app/orchestration/composite_scorer.py`: `WeightedScorer` (linear weighted average — device 20%, behavior 25%, network 25%, transaction 15%, behavioral 15%), `MaxScorer` (highest single agent score), and `EnsembleScorer` (weighted combination of Weighted at 70% and Max at 30%). The `RiskEngine` in `app/services/risk_engine.py` ties the coordinator and scorer together into a complete scoring pipeline.

**Risk orchestrator agent.** Member 2 wraps the scoring pipeline in the `RiskOrchestrator` class in `app/agents/orchestrator.py`, which exposes `score_transaction()`, `score_with_plan()` (for creating a new pipeline with a specific strategy), and `benchmark()` (for running all strategies and comparing timings). The `orchestrator_agent` is an LLM-based agent (gpt-4o-mini) that can coordinate sub-agent tool calls.

**Scoring mode configuration.** Member 2 defines the `ScoringStrategy` enum and ensures the composite scores map to decisions using the threshold table (approve < 30, review 30–69, decline >= 70).

**Error handling.** If any agent fails or times out, the coordinator uses a safe fallback score from the fast path function and continues. The system never crashes because one agent errored.

**Frontend dashboard.** Member 2 builds the frontend React application in `frontend-react/` using TanStack Start + Vite, Tailwind v4, shadcn/ui, and Framer Motion. The dashboard provides seven route pages: landing (index), authentication (auth), progress dashboard, admin panel, and three agent detail pages (orchestrator, behavior, device). State management uses TanStack Query with 5-second polling for real-time data. Member 2 configures the build process (`bun run build`) and ensures the output is placed in `app/frontend/` where the FastAPI `StaticFiles` mount serves it.

### Files Member 2 Owns

`app/agents/orchestrator.py`, `app/orchestrator/orchestrator.py`, `app/orchestrator/policy.py`, `app/orchestrator/__init__.py`, `app/orchestration/coordinator.py`, `app/orchestration/composite_scorer.py`, `app/orchestration/pipeline.py`, `app/orchestration/__init__.py`, `app/services/risk_engine.py`, `app/services/__init__.py`, `frontend-react/` (entire directory).

-----

## 7. Member 3 — Transaction Fraud Engineer

### Role Summary

Member 3 builds the transaction analysis agent — the deepest and most complex of the five specialist agents. It uses a **two-layer hybrid architecture**: Layer 1 is a hard rule engine that blocks definitively fraudulent transactions in under 10ms, and Layer 2 is an XGBoost ML model that scores the remaining 95% of transactions with nuanced, explainable predictions.

The hybrid approach is deliberate: hard rules handle the ~5% of transactions that are unambiguously fraud with zero latency and 100% explainability. The ML model handles everything rules miss — subtle correlations, feature interactions, and evolving patterns that rules cannot capture. Fraudsters can probe hard rule thresholds, but the ML model's weights are invisible and retrain weekly.

All velocity tracking throughout both layers uses **SQLAlchemy queries against the `transactions` table** — not Redis. The core helper `_count_orders()` runs parameterized SQL queries with timestamp-based time windows across four dimensions (customer, device, IP, phone). This avoids the operational complexity of maintaining Redis while keeping all state in the primary database.

### Core Responsibilities

**Layer 1 — Hard Rule Engine.** Member 3 implements four definitive hard rules, each designed to catch an unambiguous fraud pattern. All rules query the database via SQLAlchemy rather than external caches:

- **Card testing attack:** Uses `_detect_card_testing()` which queries the `transactions` table via SQL for all transactions from the same `device_fingerprint` in the last 7 days with amounts under $20.00. If there are 5 or more such micro-transactions, the pattern is flagged. The signal value (`small_txns_count`) is scored via `score_from_signal()` if the pattern is severe enough.

- **Extreme velocity:** Uses `compute_velocity_score()` which runs SQL queries across four dimensions (customer, device, IP, phone) in four time windows (1h, 6h, 24h, 7d). The critical metric is `max_1h` — the maximum order count across all dimensions in the last hour. If `max_1h >= 10`, the velocity score reaches 85 and hard escalation occurs. Hardcoded thresholds: 10+ in 1h → score 85, 5+ → 60, 3+ → 35; 20+ in 24h → 80, 10+ → 50; amount over $5000 in 24h → +40.

- **Freight forwarder address:** Detects reshipping service addresses through three layers — keyword matching on the address string ("freight", "forwarder", "pmb", "mailbox", "ups store", etc.), static ZIP code lookup against known freight forwarder hubs (Miami 33166/33126/33172, NYC 10001/11101, etc.), and a chargeback-derived hotlist table in PostgreSQL that learns from past fraud via SQL queries. All three layers are self-contained with no external API.

- **CVV missing + AVS no-match combined:** Blocks when CVV is not provided AND the AVS result is "N" (neither street nor ZIP matches). This combination is the definitive signature of a card number obtained from a data breach dump.

If any hard rule fires, the agent returns score=100, hard_blocked=true, and never calls the ML model.

**Layer 2 — XGBoost ML Scoring Engine.** For transactions that pass all hard rules, Member 3 builds a complete ML inference pipeline:

- **BIN lookup service** (`services/bin_lookup.py`): Queries a self-hosted PostgreSQL BIN database (with external API fallback for development) to get the issuing country, card type (credit/debit/prepaid/gift/virtual), and issuing bank. A 2-second hard timeout prevents slow lookups from blocking the pipeline.

- **SQL-based velocity feature computation** (`tools/velocity_checker.py`): Computes three soft velocity counts using `_count_orders()` SQL queries — card velocity (10-min window by card identifier), IP velocity (5-min window by IP), and user velocity (60-min window by customer_id). These become numeric ML features, not hard blocks. All queries use the `transactions` table with timestamp-based `WHERE` clauses.

- **25-feature engineering** (`ml/feature_engineering.py`): Assembles a 25-feature vector from the transaction payload, velocity counts (from SQL), BIN data (from PostgreSQL BIN table), device enrichment fields from Member 5, and database queries (user history, chargebacks via SQL). Features span 9 groups: amount (amount + log), temporal (hour, day, weekend), velocity (3 card/ip/user counts from SQL), card verification (AVS encoded, CVV missing), address (country match, ZIP match, freight forwarder), BIN/device (bin_country_match, is_vpn, is_proxy, is_prepaid), merchant risk multiplier, user history (account age, chargebacks 90d, return rate, total orders, is_new_account — all from SQL), and behavioral context (amount vs user avg ratio from SQL, is_micro_transaction).

- **XGBoost inference** (`ml/model_inference.py`): Loads a pre-trained XGBoost classifier at startup (single load, not per-request). Runs inference via thread pool to avoid blocking the async event loop. Scales the fraud probability (0.0–1.0) to a 0–100 score using a non-linear mapping. If the model file is unavailable, falls back to score=50 with an `ml_model_unavailable` flag.

- **SHAP explainability** (`ml/shap_explainer.py`): Runs a pre-built SHAP TreeExplainer on every ML-scored transaction to compute per-feature contribution values. Returns the top 5 contributing features with their contribution magnitudes and feature values. This provides compliance-grade auditability for every decision.

**Score combination logic.** The final score follows these rules: hard block → score=100, ML unavailable → score=50, normal ML → ml_score directly (soft rule signals are already features in the model and are NOT added on top to avoid double-counting).

**Offline model training pipeline.** Member 3 builds the training pipeline in `ml/model_trainer.py` that runs weekly (GitHub Actions, Monday 2 AM UTC):

- Loads labeled transactions from `fraud_labels` via SQL — confirmed fraud (label=1 from chargebacks, arriving 30–90 days after transaction) and confirmed legitimate (label=0 from 120-day no-dispute assumption, assigned by nightly batch job)
- Reconstructs 25-feature vectors using the exact same `compute_features()` function used at inference time (training-inference consistency). Velocity features are computed via the same SQL queries used at inference — not Redis.
- Trains XGBoost with parameters tuned for fraud: 300 trees, max_depth=6, learning_rate=0.05, scale_pos_weight compensating for severe class imbalance, stratified 5-fold cross-validation targeting AUC-ROC > 0.85
- Saves model, SHAP TreeExplainer, and metadata to `models/` directory
- Initial training uses the IEEE-CIS Fraud Detection dataset (590,540 real transactions from Kaggle) with defaults for features not available in that dataset

**SQL-based velocity state management.** All velocity tracking uses SQLAlchemy queries on the `transactions` table, not Redis. The core helper is `_count_orders(**filters)` which runs parameterized `SELECT count, amount FROM transactions WHERE {column} = {value} AND timestamp >= {window}` for each time window (1h, 6h, 24h, 7d). Velocity is computed across four dimensions: `customer_id`, `device_fingerprint`, `ip_address`, and `phone_number`. The four openai function tools (`check_customer_velocity`, `check_device_velocity`, `check_ip_velocity`, `check_phone_velocity`) each call the same SQL helper with their respective filter. The `transactions` table is indexed on all four dimension columns plus `timestamp` for query performance.

### Files Member 3 Owns

`app/agents/transaction_agent.py`, `app/tools/__init__.py`, `app/tools/fraud_patterns.py`, `app/tools/velocity_checker.py`, `ml/feature_engineering.py`, `ml/model_trainer.py`, `ml/model_inference.py`, `ml/shap_explainer.py`, `services/bin_lookup.py`, `models/` (generated model files).

-----

## 8. Member 4 — Behavioral AI Engineer

### Role Summary

Member 4 detects fraud through user behavior. Their work covers two agents: the Behavioral Agent (transaction-level behavior — velocity, session patterns, COD history) and the Behavioral Bio Agent (user-level biometrics and profile analysis — login patterns, session patterns, typing simulation, mouse behavior, profile stability). Member 4 also owns all testing for the project — unit tests, integration tests, performance tests, and test infrastructure.

### Core Responsibilities

**Behavior agent — order velocity.** Member 4 implements `_check_order_velocity()` in `app/agents/behavior_agent.py`. This function counts orders from the same customer or phone number in the last 1 hour and 24 hours. Returns per-window counts as signal values.

**Behavior agent — session anomaly.** Member 4 implements `_check_session_anomaly()` to compare the session duration against an expected minimum (`max(30 seconds, amount * 0.5)`). Returns an anomaly score (0–0.9) scaled by how short the session is relative to the expected duration.

**Behavior agent — cart value anomaly.** Member 4 implements `_check_cart_value_anomaly()` to compute the customer's historical average transaction amount and compare the current amount against it. Returns the deviation ratio as a signal value.

**Behavior agent — COD refusal rate.** Member 4 implements `_check_cod_refusal_rate()` to query the customer's COD history and compute a simulated refusal rate. The special test customer `FRIENDLY_REPEAT_001` always returns a high refusal rate for demo purposes.

**Behavior agent (fast path).** Member 4 implements `fast_path_behavior()` that runs all four checks, scores each via `score_from_signal()` with behavioral thresholds, averages them, and returns `AgentScoreOutput` with confidence 0.85.

**Behavioral bio — login anomaly.** Member 4 implements `_analyze_login_anomaly()` in `app/tools/behavior_analysis.py`. Analyzes 30-day login history: distinct IPs, user-agents, and IP change frequency. Scores are additive — more diversity equals higher risk.

**Behavioral bio — session pattern.** Member 4 implements `_analyze_session_pattern()` to compute z-scores of session duration against historical averages, and amount-to-duration ratio deviation. Statistical outliers produce additive scores.

**Behavioral bio — typing biometrics.** Member 4 implements `_analyze_typing_biometrics()` to estimate typing characteristics from available session data. Detects automation signals (very short sessions with high amounts, implausible typing speeds).

**Behavioral bio — mouse behavior.** Member 4 implements `_analyze_mouse_behavior()` to detect bot-like interaction patterns. Very short sessions immediately return high risk. Longer sessions are scored on simulated movement naturalness.

**Behavioral bio — user behavior profile.** Member 4 implements `_analyze_user_behavior_profile()` to compute a 90-day stability score based on IP diversity, IP change frequency, and transaction hour diversity. Low stability produces penalty points.

**Behavioral bio scoring.** Member 4 implements `compute_behavioral_intelligence_score()` that combines all five sub-analyses, collects signals exceeding score 30, and produces a final score capped at 100 with max 6 reason codes.

**LLM agents.** Member 4 creates both the `behavior_agent` and `behavioral_agent` (gpt-4o-mini) with their respective function tools.

**Test ownership.** Member 4 owns all testing for the project — unit tests, integration tests, performance tests, and test infrastructure. Member 4 maintains the test suite in `app/tests/`, writes new test scenarios as agents are built, ensures coverage targets are met, and runs the CI test pipeline. This includes writing tests for every member's code, maintaining the five end-to-end scenarios (`test_scenarios.py`), the validation service tests (`test_validation_service.py`), and the compliance guardrail tests (`test_compliance_guardrail.py`). Member 4 also drives the minimum 70% code coverage requirement and measures p95 latency of the fast path.

### Files Member 4 Owns

`app/agents/behavior_agent.py`, `app/agents/behavioral_agent.py`, `app/tools/behavior_analysis.py`, `app/tests/` (entire test suite).

-----

## 9. Member 5 — Device & Network Security Engineer

### Role Summary

Member 5 analyzes device and network signals. Their work covers two agents: the Device Agent (fingerprint reuse, IP geolocation, proxy/VPN detection, user-agent consistency) and the Network Agent (fraud graph analysis with NetworkX, COD address density). The device agent also enriches the shared payload with IP country, VPN status, and proxy status for use by the transaction agent.

### Core Responsibilities

**Device agent — fingerprint reuse.** Member 5 implements `_check_device_fingerprint_reuse()` in `app/agents/device_agent.py`. Queries the last 30 days of transactions for the same `device_fingerprint`. Returns the count of distinct customers using this device (excluding current) and the total transaction count. A device shared across many customers is a strong fraud ring signal.

**Device agent — IP geolocation mismatch.** Member 5 implements `_check_ip_geolocation_mismatch()` to perform a mock geolocation lookup on the customer's IP address. Determines the geographic region from IP prefix heuristics, compares it to the shipping address state, and returns a mismatch score (0.0 for match, 0.7 for complete mismatch).

**Device agent — proxy/VPN detection.** Member 5 implements `_check_proxy_vpn()` to check whether the IP address falls in known private (10.x.x.x) or documentation (203.0.113.x) ranges. Returns a boolean proxy flag with confidence 0.9 if detected.

**Device agent — user-agent consistency.** Member 5 implements `_check_user_agent_consistency()` to query the customer's last 5 transactions and compare their user-agent strings. Returns an anomaly score (0–0.8) based on how many different user-agents the customer has used historically.

**Device agent (fast path).** Member 5 implements `fast_path_device()` that runs all four checks, scores each via `score_from_signal()` with device thresholds, averages them, and returns `AgentScoreOutput` with confidence 0.85.

**Payload enrichment.** After the device agent runs, Member 5 writes `ip_country`, `is_vpn`, and `is_proxy` onto the shared transaction payload. These three values are read by Member 3's transaction agent for BIN country mismatch analysis. This enrichment must happen before Member 3 uses those fields.

**Network agent — fraud graph.** Member 5 implements `_build_fraud_graph()` in `app/agents/network_agent.py`. Fetches 60 days of transactions and builds a NetworkX graph where nodes represent customers, devices, phones, and addresses. Edges connect customers to their associated entities. Finds connected components — if a component contains multiple customers sharing the same device, phone, or address, it is a fraud ring. Returns component metadata and linked order IDs.

**Network agent — COD address density.** Member 5 implements `_check_cod_address_density()` to compute how many COD orders share the shipping address versus a system-wide baseline. A density ratio above 2.0 is considered elevated.

**Network agent (fast path).** Member 5 implements `fast_path_network()` that runs graph analysis and density checks, combines the signals, and returns `AgentScoreOutput` with linked order IDs as evidence.

**LLM agents.** Member 5 creates both the `device_agent` and `network_agent` (gpt-4o-mini) with their respective function tools.

### Files Member 5 Owns

`app/agents/device_agent.py`, `app/agents/network_agent.py`, `app/tools/ip_checker.py` (if created), `app/tools/geolocation.py` (if created).

-----

## 10. Member 6 — Backend API Engineer

### Role Summary

Member 6 builds the entire API infrastructure. This is the layer that all merchants interact with directly, and it is the glue that connects every other component. Member 6 also owns the database models, WebSocket real-time system, and authentication endpoints.

### Core Responsibilities

**Main scoring endpoint (`POST /api/score`).** This is the core endpoint the entire platform exists to serve. It validates the request body against the `TransactionIn` Pydantic schema, checks the in-memory rate limiter (30 req/min per API key, sliding window), optionally authenticates the user from a JWT Bearer token, and passes the transaction to either the V1 legacy orchestrator or the V2 pipeline (controlled by `?v2=true` query parameter). The endpoint also supports `?reasoning=true` for LLM-powered analysis and `?strategy=weighted|max|ensemble` for alternative scoring modes. After scoring, it broadcasts the result via WebSocket and returns the `TransactionDecision`.

**Transaction listing endpoint (`GET /api/transactions`).** Paginated transaction listing with optional `status` filter (approve/review/decline/pending). Returns transactions ordered by timestamp descending with total count for pagination.

**Transaction detail endpoint (`GET /api/transactions/{order_id}`).** Returns the full details of a single transaction by `order_id`. Returns 404 if not found.

**Decision override endpoint (`POST /api/transactions/{order_id}/override`).** Allows an analyst to override a transaction's decision. Updates the transaction record with the new decision and override metadata, creates an AuditLog entry tracking the change.

**Statistics endpoint (`GET /api/stats`).** Returns total scored transactions and counts per decision type (approve, review, decline, pending). Used by the dashboard for KPI cards.

**Risk distribution endpoint (`GET /api/risk-distribution`).** Returns a histogram of risk scores across five buckets: 0–20, 21–40, 41–60, 61–80, 81–100. Used by the dashboard for the risk chart.

**Agent status endpoint (`GET /api/agents/status`).** Returns real-time status for all five agents — online status, total scored, average score, average latency in milliseconds, and weight. Computed from the last 200 non-pending transactions.

**Data generation endpoint (`POST /api/generate`).** Generates synthetic transaction data for testing and demo purposes. Supports four patterns: "clean" (normal transactions), "cod_fraud" (COD fraud ring), "card_testing" (card testing burst), and "friendly_fraud" (friendly fraud pattern). Each pattern generates domain-appropriate transactions with a timestamp suffix to avoid order ID conflicts.

**Generate and score endpoint (`POST /api/generate/score-all`).** Generates and optionally scores transactions in a single call. Returns per-transaction results with decision, risk score, and latency.

**Auth endpoints.** Member 6 builds four auth endpoints:
- `POST /api/auth/register` — Creates a new dashboard user with hashed password and a random 24-byte hex API key
- `POST /api/auth/login` — Validates credentials and issues JWT access token (30 min) and refresh token (7 days)
- `POST /api/auth/refresh` — Issues new token pair from a valid refresh token
- `GET /api/auth/me` — Returns the current authenticated user's profile

**WebSocket real-time feed.** Member 6 implements three WebSocket endpoints (`/api/ws/dashboard`, `/api/ws/transactions`, `/api/ws/alerts`) that authenticate via JWT token query parameter and maintain per-channel connection pools. The `broadcast()` function pushes JSON messages to all connected clients in a channel, removing dead connections. The `notify_new_transaction()` function broadcasts to the dashboard and transactions channels on every scoring event, and to the alerts channel for high-risk (score > 50) transactions. Each WebSocket supports ping/pong keepalive.

**Database models.** Member 6 defines all SQLAlchemy ORM models in `app/db/models.py`: `Transaction` (23 columns including id, order_id, customer_id, amount, decision, risk_score, confidence, agent_scores_json, reason_codes_json, latency_ms, scoring_path, overridden, override_decision, override_by, etc.), `AuditLog` (7 columns including id, order_id, event_type, previous_decision, new_decision, details_json, created_at), and `User` (8 columns including id, username, email, hashed_password, role, disabled, api_key, created_at). Also handles async engine creation with PostgreSQL priority and SQLite fallback (auto-creates `fraud_demo.db`).

**Database seeding.** Member 6 builds the synthetic data seeder in `app/db/seed.py` that generates approximately 49 representative transactions across all four patterns (20 clean, 8 COD fraud, 15 card testing, 6 friendly fraud) with realistic data distributions and timestamps spanning 7 days.

**Pydantic schemas.** Member 6 defines all request/response schemas in `app/api/schemas.py`: `TransactionIn`, `TransactionDecision`, `AgentScoreOutput`, `OverrideRequest`, `LoginRequest`, `RegisterRequest`, `RefreshRequest`, `TokenResponse`.

### Files Member 6 Owns

`app/api/routes.py`, `app/api/auth_routes.py`, `app/api/schemas.py`, `app/api/ws.py`, `app/api/main.py`, `app/db/models.py`, `app/db/seed.py`, `app/cache/redis_client.py`, `app/cache/__init__.py`.

-----

## 11. Member 7 — DevOps, Deployment & Compliance Engineer

### Role Summary

Member 7 is responsible for making everything runnable, deployable, and observable. Currently, Claudiya.ai runs as a bare FastAPI application with local SQLite for development. Member 7's work — Docker containerization, CI/CD pipelines, and monitoring infrastructure — is planned but not yet implemented. Member 7 is also the final checkpoint before any fraud decision leaves Claudiya.ai — they own the guardrail, compliance, validation, and immutable audit log that ensure decisions are safe, fair, and explainable.

### Core Responsibilities

**Planned — Docker containerization.** Member 7 will write a `Dockerfile` that packages the application with the correct Python version, system dependencies, non-root user, and health check endpoint. This has not been started yet — the application currently runs via `uvicorn` directly.

**Planned — Docker Compose for local development.** A `docker-compose.yml` will be created to spin up the API server, PostgreSQL, Redis, Grafana, and Prometheus with a single command. Not yet implemented — local development uses SQLite with optional manual PostgreSQL connection.

**Planned — CI/CD pipelines.** GitHub Actions workflows for CI (test suite on PR) and deployment (auto-deploy on merge to main) will be created. Currently there are no CI/CD pipelines.

**Planned — Railway deployment.** Railway deployment configuration (`deployment/railway.json`) will be created with start command, health check path, and restart policy. Not yet implemented.

**Planned — Monitoring.** Prometheus scraping the API's `/metrics` endpoint and Grafana dashboards for requests per minute, latency, decision distribution, agent error rate, DB pool availability, and Redis memory usage will be configured. Neither Prometheus nor Grafana are currently set up — the `/metrics` endpoint does not exist yet.

**TestSprite integration.** Member 7 configures the TestSprite MCP server integration for automated UI testing. The `opencode.json` file configures the TestSprite MCP server with the API key. The `.mjs` scripts (`_exec_tests.mjs`, `_run_testsprite.mjs`) automate test execution, and `_gen_plans.mjs` generates standardized test plans.

**Output validation.** Member 7's `ValidationService.validate_output()` checks structural integrity: all required fields present, risk score within [0, 100], confidence within [0, 1], no negative agent scores, no more than 8 reason codes, decision consistency with score (approve < 30, decline > 70), and no PII patterns (SSN, 16-digit numbers, emails, 10-digit phones) in reason codes.

**Confidence validation.** `ValidationService.validate_confidence()` enforces minimum confidence thresholds per decision type: approve requires >= 0.75 and risk <= 30, review requires >= 0.60 and risk <= 70, decline requires >= 0.80 and risk >= 70.

**Compliance checks.** `ValidationService.run_compliance_checks()` enforces three regulations: GDPR (at least 1 reason code for explainability), AML (transactions >= $10,000 must be review or decline), and KYC (review decisions need customer verification).

**Bias detection.** `ValidationService.detect_bias()` compares mean risk scores between groups (by region, by payment method) against a maximum disparity threshold. Region max disparity is 0.15. Payment method (COD vs. card) max disparity is 0.10. Biases are logged but do not change the current decision — they inform model and policy improvements over time.

**Human review escalation.** `ValidationService.should_escalate_to_human()` checks for escalation triggers: confidence below 0.60, low confidence (< 0.70) combined with high risk (> 60), borderline score in [25, 35], confidence validation failure, or any bias check failure.

**Reason code computation.** `compute_reason_codes()` in `app/guardrail/guardrail.py` collects evidence from all agents with scores above 20, producing a maximum of 8 human-readable reason codes.

**Decision thresholding and fraud ring escalation.** `apply_guardrails()` in `app/guardrail/guardrail.py` applies decision thresholds (approve < 30, decline > 70), escalates fraud-ring-linked transactions to review even if the score suggests approval, and performs a documented fairness check that prohibits raw location-based declines.

**Fairness policy enforcement.** The `_check_fairness()` function documents the policy that raw location is never used as a decline signal. Location risk must come indirectly through network agent COD density or device agent IP geolocation mismatch.

**Compliance guardrail agent (LLM).** Member 7 creates the `compliance_guardrail_agent` (gpt-4o-mini) for complex borderline cases. It enforces: never approve if risk >= 30, never decline if risk <= 70, escalate if confidence < 0.60 or risk in [25, 35], escalate if bias checks fail.

**Compliance policy configuration.** Member 7 maintains `app/configs/policies.py` — the file that defines `BiasPolicy`, `ConfidencePolicy`, `SafetyPolicy`, `PiiRules`, `CompliancePolicy`, and `HumanReviewPolicy`.

**Immutable audit log.** Member 7 ensures every fraud decision is written to the `audit_log` table — insert-only, never updated or deleted.

### Files Member 7 Owns

`app/agents/compliance_guardrail.py`, `app/guardrail/guardrail.py`, `app/guardrail/__init__.py`, `app/services/validation_service.py`, `app/configs/policies.py`, `app/configs/__init__.py`, `opencode.json`. Planned files: `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`, `deployment/railway.json`, `monitoring/prometheus.yml`, `monitoring/grafana/dashboards/claudiya.json`.

-----

## 12. Database Design

Every member who writes database queries must understand the schema and access patterns.

### Entity Relationship Overview

The system uses three core tables managed by SQLAlchemy ORM with async session support. The database engine auto-detects PostgreSQL or falls back to SQLite (auto-creating `fraud_demo.db` in the project root).

### Table: `transactions`

This is the primary data table — every transaction analysis request and its result is stored here.

| Column | Type | Details |
|--------|------|---------|
| `id` | Integer | Primary key, auto-increment |
| `order_id` | String | Unique, indexed, NOT NULL |
| `customer_id` | String | Indexed, NOT NULL |
| `amount` | Float | NOT NULL |
| `currency` | String | Default "USD" |
| `payment_method` | String | enum: "card", "cod", "wallet" |
| `device_fingerprint` | String | NOT NULL |
| `ip_address` | String | NOT NULL |
| `phone_number` | String | NOT NULL |
| `shipping_address` | Text | NOT NULL |
| `user_agent` | String | NOT NULL |
| `session_duration_seconds` | Float | NOT NULL |
| `timestamp` | DateTime | Default: utcnow |
| `decision` | String | Default "pending", enum: "approve", "review", "decline", "pending" |
| `risk_score` | Float | Nullable, 0–100 |
| `confidence` | Float | Nullable, 0–1 |
| `agent_scores_json` | Text | Nullable, JSON dict of per-agent scores |
| `reason_codes_json` | Text | Nullable, JSON array of reason strings |
| `latency_ms` | Float | Nullable, total pipeline time in ms |
| `scoring_path` | String | Default "fast", enum: "fast", "reasoning", "hybrid" |
| `overridden` | Integer | Default 0, boolean flag |
| `override_decision` | String | Nullable, analyst decision |
| `override_by` | String | Nullable, analyst name |

### Table: `audit_log`

Immutable record of every fraud decision. Insert-only — never updated or deleted.

| Column | Type | Details |
|--------|------|---------|
| `id` | Integer | Primary key, auto-increment |
| `order_id` | String | Indexed, NOT NULL |
| `event_type` | String | NOT NULL, enum: "score", "override" |
| `previous_decision` | String | Nullable, for overrides |
| `new_decision` | String | Nullable, for overrides |
| `details_json` | Text | Nullable, JSON payload with full decision context |
| `created_at` | DateTime | Default: utcnow |

### Table: `users`

Dashboard login accounts for merchant fraud analysts.

| Column | Type | Details |
|--------|------|---------|
| `id` | Integer | Primary key, auto-increment |
| `username` | String | Unique, indexed, NOT NULL |
| `email` | String | Unique, NOT NULL |
| `hashed_password` | String | NOT NULL, bcrypt hash (12 rounds) |
| `role` | String | Default "analyst", enum: "admin", "analyst", "viewer" |
| `disabled` | Boolean | Default False |
| `api_key` | String | Unique, Nullable, random 24-byte hex |
| `created_at` | DateTime | Default: utcnow |

### Access Patterns

- All transaction queries filter by indexed columns (`order_id`, `customer_id`) for performance
- Transaction listing queries use `ORDER BY timestamp DESC` with `LIMIT`/`OFFSET` pagination
- Agent statistics are computed from the last 200 non-pending transactions in a single query
- Fraud pattern detection queries use 7-day, 30-day, or 60-day windows depending on the pattern
- Velocity queries use 1-hour, 6-hour, 24-hour, and 7-day windows across four dimensions
- Audit log is append-only — no UPDATE or DELETE operations are ever executed against it

-----

## 13. Inter-Member Dependency Map

### Hard Dependencies (blocking — cannot build without these)

| Member | Depends On | For What |
|--------|------------|----------|
| Member 3 | Member 5 | `ip_country`, `is_vpn`, `is_proxy` on payload for BIN geo-mismatch and ML features |
| Member 3 | Member 6 | Database session (`async_session`) for all velocity SQL queries, chargeback history, and user data |
| Member 3 | Member 6 | `fraud_labels` table and `bin_database` table for ML model training and BIN lookup |
| Member 4 | Member 6 | Database session for behavioral event persistence and historical queries |
| Member 5 | Member 6 | Database session for impossible travel, fingerprint history, and fraud graph |
| Member 7 | Member 6 | Database session for audit log, validation queries |
| Member 2 | Members 3, 4, 5 | Agent results to compute composite score |
| Member 6 | Member 2 | `score_transaction()` / `RiskOrchestrator` entry point for `/api/score` |
| Member 6 | Member 7 | `validate_transaction_output()` for guardrail validation |
| Member 1 | All members | Integration testing after all components are merged |
| All agents | Member 1 | `main.py` startup, shared config, dependencies |
| All members | Member 7 | Docker, CI/CD, deployment infrastructure |

### Interface Agreements (must be confirmed between members before coding)

| Agreement | Members Involved | What to Agree On |
|-----------|-----------------|------------------|
| Transaction input schema | Members 2, 3, 4, 5, 6 | Field names, types, optional vs required in `TransactionIn` |
| Agent result schema | Members 2, 3, 4, 5 | Score field name, confidence, explanation, evidence format in `AgentScoreOutput` |
| Device enrichment fields | Members 2, 3, 5 | Exact field names for `ip_country`, `is_vpn`, `is_proxy` on payload |
| Composite result schema | Members 2, 6, 8 | Field names in `TransactionDecision` — decision, risk_score, confidence, agent_scores, reason_codes |
| Fast path function signatures | Members 2, 3, 4, 5 | All `fast_path_*` functions must accept `Transaction` and return `AgentScoreOutput` |
| OpenAI agent definitions | Members 2, 3, 4, 5 | Agent name, instructions, model, tools, output type conventions |
| Valid flag/reason strings | Members 3, 4, 5, 8 | The exact string values for every possible fraud flag and reason code |

-----

## 14. GitHub Workflow & Branching

### Branch Structure

```
main          ← production-ready, auto-deploys on merge
feature/*     ← individual member work
```

| Member | Branch Name |
|--------|-------------|
| Member 1 | `feature/architecture` |
| Member 2 | `feature/orchestrator` |
| Member 3 | `feature/transaction-agent` |
| Member 4 | `feature/behavioral-agent` |
| Member 5 | `feature/device-network-agent` |
| Member 6 | `feature/backend` |
| Member 7 | `feature/devops` |
| Member 7 | `feature/guardrails` |

### Daily Workflow

Every team member follows this sequence every day:

Pull the latest `main` before starting work. Work on the feature branch. Commit frequently with descriptive messages. Push the branch to GitHub. When a logical unit of work is complete, open a pull request from the feature branch to `main`. Member 1 reviews the PR, confirms CI passes, and merges it. The merge triggers Railway to automatically redeploy.

### Commit Message Convention

Commits must follow the format: `type: short description`

Valid types: `feat` (new feature), `fix` (bug fix), `test` (tests only), `docs` (documentation), `refactor` (restructuring without behavior change), `chore` (maintenance tasks).

### Pull Request Rules

No PR merges without Member 1's approval. No PR merges if CI tests are failing. No direct commits to `main`. Feature branches are deleted after merge.

-----

## 15. Testing Requirements

### What Each Member Must Test

**Member 2 (Orchestrator):** Test that composite scoring formula produces correct results for known inputs across all three strategies (weighted, max, ensemble). Test that hard block passthrough correctly forces score=100. Test that one agent erroring does not crash the orchestrator. Test that V1 and V2 pipelines produce identical results for the same input. Test that stage timings are recorded correctly.

**Member 3 (Transaction Agent):** Test every hard rule independently — card testing attack, extreme velocity, freight forwarder ZIP match, freight forwarder keyword match, CVV+AVS combined failure. Test that hard block returns score=100 and hard_blocked=true. Test that a clean transaction is not hard blocked. Test that ML model unavailable flag appears when model not loaded. Test that agent never crashes — returns score=50 on exception. Test that output shape is always complete (score 0–100, flags list, hard_blocked bool, ml_fraud_probability 0.0–1.0). Test that feature vector has exactly 25 features and all are finite. Test that feature engineering uses identical transformations as training script. Test that SQL velocity queries (`_count_orders()`) return correct counts for each time window (1h, 6h, 24h, 7d) and each dimension (customer, device, IP, phone).

**Member 4 (Behavioral Agent):** Test that velocity check correctly counts orders in time windows. Test that session anomaly produces higher scores for shorter sessions. Test that cart value deviation is computed correctly. Test that COD refusal rate handles edge cases (no history, all COD, mixed). Test the behavioral bio agent's five analyses with synthetic input data. Test graceful handling of missing behavioral data.

**Member 5 (Device & Network Agent):** Test fingerprint reuse detection with known fingerprint sharing scenarios. Test IP geolocation mismatch with controlled IP/address pairs. Test proxy/VPN detection with known proxy and non-proxy IPs. Test user-agent consistency with single vs. multiple agents. Test fraud graph construction with a known set of transactions. Test that payload enrichment correctly adds `ip_country`, `is_vpn`, `is_proxy`.

**Member 6 (API):** Test that score endpoint returns 200 for valid requests. Test that malformed request body returns 422. Test that rate-limited client returns 429. Test that WebSocket receives push on new transaction. Test that auth endpoints correctly issue, refresh, and validate JWT tokens. Test that invalid credentials return 401. Test that transaction listing supports filtering and pagination. Test that override creates audit log entry.

**Member 7 (Guardrail):** Test that clean decisions pass all validation. Test that missing fields, out-of-range scores, and negative agent scores are caught. Test that confidence thresholds are enforced per decision type. Test that bias detection correctly identifies disparate impact. Test that AML compliance flags high-value transactions. Test that human review escalation triggers for low confidence, borderline scores, and bias failures. Test that reason code computation respects the 8-code maximum.

### Test Ownership

Member 4 owns all testing strategy and execution: unit tests, integration tests, performance tests, and test infrastructure. This includes maintaining the test suite in `app/tests/`, writing new test scenarios, ensuring coverage targets are met, and running the CI test pipeline.

### Integration Tests

The `app/tests/test_scenarios.py` file contains five end-to-end scenario tests:

- **`test_clean_order_fast_path`** — Scores a clean order and validates the decision is approve or review with risk < 50 and latency < 500ms.
- **`test_cod_fraud_ring`** — Scores a COD fraud ring transaction and validates the decision is review or decline with risk > 30 and network score > 20.
- **`test_card_testing_burst`** — Scores a card testing transaction and validates risk > 20 and behavior score > 20.
- **`test_friendly_fraud_pattern`** — Scores a friendly fraud transaction and validates risk > 10 with reason codes mentioning COD or refusal.
- **`test_api_score_endpoint`** — Hits the actual HTTP endpoint and validates 200 status, valid decision, risk 0–100, agent_scores present.
- **`test_list_transactions`** — Validates paginated transaction listing returns correct structure.
- **`test_override_endpoint`** — Hits the override endpoint and validates decision changes.

The `app/tests/test_validation_service.py` file has 18 unit tests across 6 classes covering output validation, confidence validation, bias detection, human review escalation, compliance checks, and end-to-end validation flows.

The `app/tests/test_compliance_guardrail.py` file has 5 tests covering clean decisions, low confidence escalation, borderline escalation, negative agent scores, and missing field detection.

### Minimum Coverage Requirement

All modules: 70% code coverage minimum, enforced by the CI pipeline.

### Performance Requirement

Fast-path p95 latency must be under 150ms. Full pipeline (all 5 agents, V2) under 200ms. API response (stats, transactions) under 50ms. Measured with a 50-concurrent-user load test before every production release.

-----

## 16. Launch Checklist

### Infrastructure

- [ ] `docker-compose up` runs without errors from a clean clone
- [ ] Database tables create cleanly: `transactions`, `audit_log`, `users` exist
- [ ] Health check returns 200: `GET /api/stats`
- [ ] Grafana dashboards load with all metrics defined in Member 7's section
- [ ] Railway deployment succeeds
- [ ] All environment variables set in Railway — none are missing
- [ ] Database auto-seeds with synthetic data on first run

### Security

- [ ] No secrets in `.env` have ever been committed to git history
- [ ] JWT secret is a randomly generated 64-character string in production
- [ ] Rate limiting confirmed: 30 req/min enforced on `/api/score`
- [ ] Password hashing uses bcrypt with 12 rounds
- [ ] CORS origins locked to production domain (not `*`)
- [ ] HTTPS enforced in production (Railway provides SSL automatically)

### Agent Integration

- [ ] All five agents complete within 150ms each in fast path
- [ ] All five LLM agents complete within 30s each in reasoning path
- [ ] Orchestrator handles one agent failing without crashing
- [ ] Device enrichment fields (`ip_country`, `is_vpn`, `is_proxy`) visible to Transaction Agent
- [ ] Clean transaction gets risk < 30 and decision = approve
- [ ] Hard block (extreme velocity, card testing, freight forwarder, CVV+AVS) returns score=100 immediately
- [ ] Clean transaction with no hard block passes through to ML layer and gets score < 30
- [ ] ML model loads at startup and is available during runtime
- [ ] ML model unavailable gracefully falls back to score=50 with `ml_model_unavailable` flag
- [ ] SHAP explanation is populated for all non-hard-block decisions
- [ ] Feature vector assertion passes (25 features, all finite values)
- [ ] BIN lookup timeout (2 seconds) does not block the pipeline — uses neutral defaults on failure
- [ ] SQL velocity queries return correct counts for all 4 dimensions across all 4 time windows (1h, 6h, 24h, 7d)
- [ ] COD fraud ring gets network score > 20 and decision = review or decline
- [ ] Card testing pattern gets risk > 20 and behavior score > 20
- [ ] Friendly fraud pattern gets risk > 10 and COD refusal reason code

### Scoring Strategies

- [ ] Weighted scoring produces correct weighted average for known inputs
- [ ] Max scoring correctly returns the highest agent score
- [ ] Ensemble scoring correctly combines Weighted (70%) and Max (30%)
- [ ] All three strategies can be selected via `?strategy=` query parameter
- [ ] V1 legacy path and V2 pipeline produce identical results for same input

### Guardrails

- [ ] Reason codes are limited to maximum 8 per decision
- [ ] Risk score outside [0, 100] triggers validation failure
- [ ] Confidence outside [0, 1] triggers validation failure
- [ ] Negative agent scores trigger validation failure
- [ ] Approve with risk > 30 triggers inconsistency warning
- [ ] Decline with risk < 70 triggers inconsistency warning
- [ ] Low confidence (< 0.60) triggers human review escalation
- [ ] Borderline score in [25, 35] triggers escalation

### Compliance

- [ ] GDPR check requires at least 1 reason code
- [ ] AML check flags $10,000+ transactions for review or decline
- [ ] KYC check marks review decisions as needing verification
- [ ] Bias detection compares region groups with 0.15 max disparity
- [ ] Bias detection compares payment method groups with 0.10 max disparity

### API

- [ ] Full request lifecycle test passes (Section 4 scenario end-to-end)
- [ ] All 15 REST endpoints return correct status codes
- [ ] All 3 WebSocket endpoints connect, authenticate, and receive broadcasts
- [ ] Valid TransactionIn returns 200 with valid TransactionDecision
- [ ] Invalid TransactionIn (missing fields) returns 422
- [ ] Over-ratelimited client returns 429
- [ ] Invalid JWT returns 401
- [ ] Valid login returns access + refresh tokens
- [ ] Refresh token issues new token pair

### Dashboard

- [ ] Dashboard loads with all KPI cards, risk chart, threat feed, agent progress
- [ ] Search filters transactions in real time
- [ ] Agent status shows all 5 agents with scores, latency, weights
- [ ] Agent detail pages load for orchestrator, behavior, device
- [ ] Agent progress page shows pipeline visualization with audit timeline
- [ ] Admin panel shows agent health table, generation controls, guardrail toggles
- [ ] Data generation creates transactions that appear in the dashboard
- [ ] Generate and score creates scored transactions visible in the feed

### Frontend

- [ ] Frontend builds without errors: `bun run build`
- [ ] All 7 routes render without crash (dashboard, auth, progress, admin, 3 agent pages)
- [ ] Auth page indicates sign-in status correctly
- [ ] 404 page renders for unknown routes
- [ ] Error boundary renders on client-side errors
- [ ] Dark theme renders correctly across all pages
- [ ] Animations (scanlines, pulse rings, shimmer bars, staggered entrances) render correctly

### Final Integration

- [ ] All feature branches merged, no open PRs
- [ ] README complete with system architecture description
- [ ] All test suites pass: `pytest app/tests/ -v`
- [ ] Coverage at or above 70%: `pytest app/tests/ --cov=app --cov-fail-under=70`
- [ ] Demo scenario prepared: clean approve, COD ring decline, card testing decline, friendly fraud review
- [ ] WebSocket real-time updates confirmed working in browser dashboard
- [ ] End-to-end flow verified: generate → score → see in dashboard → override → see in audit log

-----

*End of Document — Claudiya.ai Full Project PRD v1.0*
