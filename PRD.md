# PRD: Claudiya.ai — Multi-Agent Fraud Detection Platform

## 1. Overview

Claudiya.ai is a production-grade, real-time fraud detection platform powered by five parallel AI agents. It fuses behavioural telemetry, device intelligence, transaction scoring, network reputation, and policy orchestration into a single sub-200ms decision pipeline with hard compliance guardrails.

**Tagline:** *Three agents. One verdict. Zero blind spots.*

---

## 2. Goals

| Goal | Description |
|---|---|
| Real-time scoring | Sub-200ms end-to-end latency for fast-path transactions |
| Multi-agent fusion | 5 parallel agents weighted by confidence, not hard rules |
| Human-in-the-loop | Admin override, audit trail, review queues |
| Compliance-first | LLM-powered guardrails enforce policy at every decision |
| Operational visibility | Live dashboard, agent health, risk distribution, threat feed |

---

## 3. Non-Goals

- Building a general-purpose ML platform
- Supporting non-fraud use cases (credit scoring, KYC)
- Real-time model training / online learning
- Mobile SDK or client-side SDK

---

## 4. Architecture

### 4.1 System Diagram

```
┌─────────────┐     ┌─────────────────────────────────────────────┐
│   Client    │────▶│              FastAPI Backend                 │
│  (React SPA)│     │  http://127.0.0.1:8000                      │
└─────────────┘     │  JWT Auth · CORS · Rate Limit               │
                    └──────────────┬──────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────────┐
                    │           Risk Orchestrator v2               │
                    │  ┌────────┐ ┌────────┐ ┌────────┐           │
                    │  │ Device │ │Behavior│ │Network │           │
                    │  │ Agent  │ │ Agent  │ │ Agent  │           │
                    │  └───┬────┘ └───┬────┘ └───┬────┘           │
                    │  ┌────────┐ ┌────────┐     │                │
                    │  │  Tx    │ │Behavioral│    │                │
                    │  │ Agent  │ │  Bio     │    │                │
                    │  └───┬────┘ └───┬────┘     │                │
                    │      └─────┬────┘          │                │
                    │            ▼               ▼                │
                    │     ┌──────────────────────────┐            │
                    │     │   Composite Scorer        │            │
                    │     │   (weighted / max / ens.) │            │
                    │     └────────────┬─────────────┘            │
                    │                  ▼                           │
                    │     ┌──────────────────────────┐            │
                    │     │   Compliance Guardrail   │            │
                    │     │   (LLM + policy engine)  │            │
                    │     └────────────┬─────────────┘            │
                    └──────────────────┼──────────────────────────┘
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │              Decision + Storage              │
                    │   SQLite / PostgreSQL · Audit Log · Redis   │
                    └─────────────────────────────────────────────┘
```

### 4.2 Stack

**Backend (Python)**
- FastAPI + Uvicorn (async)
- OpenAI Agents SDK (`gpt-4o-mini`)
- SQLite (dev) / PostgreSQL (prod)
- Redis (caching, rate-limit, WebSocket pub/sub)
- JWT auth (access 30m + refresh 7d)
- Pydantic v2 schemas

**Frontend (React)**
- TanStack Start (SSR) + Vite
- React Query (5s polling)
- Recharts (risk chart)
- Framer Motion (animations)
- Tailwind CSS v4 (design tokens)
- shadcn/ui component primitives

---

## 5. Agents

| Agent | Weight | Avg Score | Avg Latency | Function |
|---|---|---|---|---|
| Device | 0.20 | 5.7 | 98ms | Fingerprint, ASN, emulator probe, trust verdict |
| Behavior | 0.25 | 17.7 | 98ms | Session telemetry, velocity, anomaly baseline |
| Network | 0.25 | 69.1 | 98ms | IP reputation, proxy/VPN detection, ASN scoring |
| Transaction | 0.15 | 20.8 | 100ms | Amount patterns, COD flags, payment method risk |
| Behavioral Bio | 0.15 | 52.3 | 100ms | Keystroke/mouse dynamics, session bio profile |

**Scoring Modes:**
- `weighted` — linear weighted average (default)
- `max` — highest single agent score
- `ensemble` — majority vote across agent thresholds

**Decision Thresholds:**
- `approve`: score < 25
- `review`: 25 ≤ score < 60
- `decline`: score ≥ 60

---

## 6. Features

### 6.1 Dashboard
- Live KPI cards (events/sec, blocked, avg decision, precision)
- Risk surface area chart (Recharts, 24h window)
- Live threat feed (real transactions, severity-coded)
- Agent pipeline progress (3 agents with stage bars)
- Regional capacity gauges (Americas, EMEA, APAC, LATAM)

### 6.2 Search
- Real-time filtering of transactions by order_id, customer_id, decision, amount, currency
- ⌘K / Ctrl+K keyboard shortcut to focus
- Esc / × button to clear

### 6.3 Agent Detail Pages
- `/agents/orchestrator` — decision fusion, policy routing
- `/agents/behavior` — session telemetry, velocity
- `/agents/device` — fingerprint, network trust
- Each shows: score, latency, count, weight, compliance results

### 6.4 Agent Progress Page
- `/progress` — full pipeline observability
- Audit event timeline
- Per-agent stage breakdown

### 6.5 Admin Panel
- `/admin` — agent health table, policy toggle, recent activity
- Live agent status (online/offline, scores, latency)
- Policy override switches

### 6.6 Auth
- JWT-based with mock auth fallback
- Hardcoded admin: `abdulsamad9ii11@gmail.com` (role: admin)
- Supabase auth removed to avoid runtime crashes

### 6.7 Compliance & Guardrails
- 6 policy classes (CNP velocity, emulator, geo-jump, mule cluster, ASN repeat, card testing)
- LLM-powered compliance assessment
- Guardrail agent validates every decision before finalization

### 6.8 Data Generation
- `POST /api/generate` — generate N transactions by pattern
- `POST /api/generate/score-all` — generate + score through all 5 agents
- Patterns: random, clean, fraud, mixed

---

## 7. API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/agents/status` | All 5 agent stats (online, scored, avg score/latency, weight) |
| GET | `/api/stats` | Transaction totals + counts by decision |
| GET | `/api/risk-distribution` | Bucketed risk scores (0-20, 21-40, 41-60, 61-80, 81-100) |
| GET | `/api/transactions` | Paginated transaction list |
| GET | `/api/transactions/:id` | Single transaction detail |
| POST | `/api/generate` | Generate transactions |
| POST | `/api/generate/score-all` | Generate + score through agents |
| POST | `/api/auth/login` | JWT login |
| POST | `/api/auth/register` | User registration |
| POST | `/api/auth/refresh` | Refresh access token |
| GET | `/api/auth/me` | Current user info |
| WS | `/api/ws/dashboard` | Real-time dashboard updates |
| WS | `/api/ws/transactions` | Live transaction stream |
| WS | `/api/ws/alerts` | Alert notifications |

---

## 8. Design

### 8.1 Color Palette
| Token | Value | Usage |
|---|---|---|
| Background | `#000000` | Page background |
| Foreground | `#ffffff` | Body text |
| Primary | `#ffd000` | Gold accent, buttons |
| Accent | `#990000` | Red berry, secondary accent |
| Destructive | `#ff0000` | Errors, blocked transactions |
| Card | `#0a0a0a` | Surface cards |
| Border | `#222222` | Dividers, strokes |
| Gold Tint | `#f5edde` | Charts, subtle highlights |

### 8.2 Typography
- **Display:** Space Grotesk (headings)
- **Sans:** Inter (body)
- **Mono:** JetBrains Mono (data, metrics, code)

### 8.3 Animations
- Staggered card entrance (translateY + fade)
- Scanline overlay on stat cards
- Pulse-ring on live indicators
- Shimmer bar on loading skeletons
- Frame Motion `AnimatePresence` for feed items

---

## 9. Data Model

### Transactions Table
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| order_id | VARCHAR | Unique order identifier |
| customer_id | VARCHAR | Customer identifier |
| amount | FLOAT | Transaction amount |
| currency | VARCHAR | Currency code |
| payment_method | VARCHAR | Card, wallet, COD, etc. |
| device_fingerprint | VARCHAR | Device hash |
| ip_address | VARCHAR | Client IP |
| risk_score | FLOAT | 0-100 composite score |
| decision | VARCHAR | approve / review / decline / pending |
| agent_scores_json | TEXT | JSON: per-agent scores |
| latency_ms | FLOAT | Total pipeline time |
| scoring_path | VARCHAR | fast / reasoning / hybrid |
| timestamp | DATETIME | Created at |

### Audit Log Table
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| event_type | VARCHAR | create / score / override |
| order_id | VARCHAR | Related order |
| details_json | TEXT | JSON payload |
| timestamp | DATETIME | Created at |

### Users Table
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| email | VARCHAR | Unique |
| hashed_password | VARCHAR | bcrypt hash |
| role | VARCHAR | admin / analyst / viewer |
| created_at | DATETIME | Created at |

---

## 10. Performance

| Metric | Target | Actual |
|---|---|---|
| Fast-path p95 latency | < 150ms | ~120ms |
| Pipeline (5 agents) | < 200ms | ~100ms |
| API response (stats) | < 50ms | ~20ms |
| Concurrent requests | 30/min | rate-limited |
| DB query (transactions) | < 100ms | ~5ms (SQLite) |

---

## 11. Security

- JWT access tokens (30min expiry) + refresh tokens (7d)
- bcrypt password hashing (12 rounds)
- Rate limiting: 30 requests/minute
- CORS: all origins in dev, locked in prod
- No raw location as decline signal (privacy)
- No secrets in client-side code
- SQL injection prevention via parameterized queries (Pydantic + SQLite)

---

## 12. Known Limitations

1. **IPv6 required for direct PostgreSQL** — Supabase direct connection blocked on IPv4-only networks. REST API SDK works over IPv4.
2. **Mock auth in frontend** — Supabase auth removed to avoid SSR crashes. Hardcoded admin user.
3. **SQLite for development** — not suitable for production scale (>10K concurrent).
4. **No CI/CD pipeline** — manual build and deploy.
5. **Redis optional** — falls back gracefully, but WebSocket pub/sub requires it for multi-instance.

---

## 13. Future Roadmap

| Phase | Items |
|---|---|
| Q3 2026 | PostgreSQL migration, WebSocket reconnects, rate-limit dashboard |
| Q4 2026 | User roles & permissions, audit export, team management |
| Q1 2027 | Custom agent configuration UI, rule builder, webhook integrations |
| Q2 2027 | A/B testing framework, model versioning, automated retraining |

---

## 14. How to Run

```bash
# Backend
cd E:\New folder (2)
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend
cd frontend-react
node .\node_modules\vite\bin\vite.js dev --port 5173
```

- **Frontend:** http://localhost:5173
- **Backend:** http://127.0.0.1:8000
- **Admin:** abdulsamad9ii11@gmail.com (auto-auth)

---

*PRD v1.0 — June 2026*
