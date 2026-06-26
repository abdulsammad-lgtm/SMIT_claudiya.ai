# Sentinel — Real-Time Agentic Fraud Detection Platform

Multi-agent fraud detection for e-commerce with specialized COD (cash-on-del8000ivery) fraud detection. Built with Python, FastAPI, and the OpenAI Agents SDK.

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your OpenAI API key in .env
#    (Edit .env and replace your-openai-api-key-here)

# 4. Run the app
uvicorn app.api.main:app --reload
```

Open http://127.0.0.1: in your browser.

## Architecture

```
POST /api/score         # Score a transaction (merchant-facing)
GET  /api/transactions  # List transactions (dashboard)
GET  /api/transactions/{id}  # Transaction detail
POST /api/transactions/{id}/override  # Analyst override
GET  /api/stats         # Summary statistics
GET  /api/risk-distribution  # Risk score histogram
```

### Scoring Paths

- **Fast path** (default): Deterministic scoring from tool function outputs — no LLM call, under 150ms. Used for most transactions.
- **Reasoning path** (`?reasoning=true`): Runs the full OpenAI Agents SDK agent loop. Used for transactions in the `review` band or flagged fraud rings. Produces natural-language explanations.

### Three Specialist Agents

| Agent | Signals |
|-------|---------|
| **Device** | Fingerprint reuse, IP geolocation mismatch, proxy/VPN detection, user-agent consistency |
| **Behavior** | Order velocity, session duration anomaly, cart value deviation, COD refusal rate |
| **Network** | Fraud graph (NetworkX), connected components (fraud rings), COD address density |

### Guardrails

- **Explainability**: Plain-language reason codes on every decision
- **Escalation**: Borderline scores (30-70) force `review` — never auto-declined
- **Fairness**: No raw location-based decline (see code comment in `guardrail.py`)
- **Audit**: Append-only audit table with full agent outputs and timestamps
- **Rate limiting**: 30 req/min per API key on `/score`

## Demo Script

Walk through these scenarios on the dashboard:

### 1. Clean Orders
Filter to **Approved** in the dashboard. These are normal transactions with no suspicious signals. They should all show risk scores under 30 and green badges.

### 2. COD Fraud Ring
Search for `COD-FRAUD` in the transaction feed. Click any transaction. You'll see:
- High network agent score (device/phone shared across 8 accounts)
- Network graph showing connected entities
- Decision in `review` or `decline`
- Reason codes mentioning linked orders

### 3. Card-Testing Burst
Filter to **Review** or **Declined**. Find `CARD-TEST` orders. They show:
- High behavior agent score (many small orders from same device in hours)
- Very short session durations (3-12 seconds)

### 4. Friendly Fraud
Find `FRIENDLY` orders. These show:
- Elevated COD refusal rate from past history
- Moderate risk score with clear reason code
- A single transaction that looks normal but has historical red flags

### API Demo

```bash
# Score a clean transaction (fast path)
curl -X POST http://127.0.0.1:8000/api/score \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "DEMO-CLEAN-001",
    "customer_id": "CUST_DEMO",
    "amount": 59.99,
    "payment_method": "card",
    "device_fingerprint": "FP_DEMO_001",
    "ip_address": "192.168.1.50",
    "phone_number": "+15551112222",
    "shipping_address": "456 Main St, Portland, OR 97201",
    "user_agent": "Mozilla/5.0 Chrome/120.0.0.0",
    "session_duration_seconds": 300.0
  }'

# Score with reasoning path (slower, shows natural language)
curl -X POST "http://127.0.0.1:8000/api/score?reasoning=true" \
  -H "Content-Type: application/json" \
  -d '{"order_id":"DEMO-REASON-001","customer_id":"CUST_DEMO","amount":59.99,"payment_method":"card","device_fingerprint":"FP_DEMO_001","ip_address":"192.168.1.50","phone_number":"+15551112222","shipping_address":"456 Main St, Portland, OR 97201","user_agent":"Mozilla/5.0 Chrome/120.0.0.0","session_duration_seconds":300.0}'

# Get stats
curl http://127.0.0.1:8000/api/stats
```

## Testing

```bash
pytest app/tests/ -v
```

## Configuration

Edit `app/orchestrator/policy.py` to tune:
- `FAST_PATH_WEIGHTS`: Agent score weights
- `RISK_THRESHOLDS`: approve/review/decline boundaries
- `TOOL_THRESHOLDS`: Per-signal sensitivity thresholds

## Notes

- Uses **synthetic data only** — no real PII, card numbers, or customer data
- Database is SQLite (`fraud_demo.db`) — zero setup, resets on each run
- The `/api/score` endpoint is rate-limited at 30 req/min per API key
- For production, swap SQLite for Postgres and add proper API key authentication
