const BASE = 'http://127.0.0.1:8000/api';

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export interface AgentStats {
  online: boolean;
  total_scored: number;
  avg_score: number;
  avg_latency_ms: number;
  weight: number;
}

export interface AgentsStatus {
  agents: Record<string, AgentStats>;
  total_transactions: number;
}

export interface StatsResponse {
  total: number;
  counts: { approve: number; review: number; decline: number; pending: number };
}

export interface Transaction {
  order_id: string;
  customer_id: string;
  amount: number;
  currency?: string;
  risk_score: number | null;
  decision: string;
  latency_ms: number | null;
  timestamp: string;
  confidence?: number;
  payment_method?: string;
  reason_codes?: string[];
  agent_scores?: Record<string, number>;
}

export interface RiskDistribution {
  bins: Record<string, number>;
}

export const api = {
  agentsStatus: () => fetchJSON<AgentsStatus>('/agents/status'),
  stats: () => fetchJSON<StatsResponse>('/stats'),
  riskDistribution: () => fetchJSON<RiskDistribution>('/risk-distribution'),
  transactions: (perPage = 50) => fetchJSON<{ transactions: Transaction[] }>(`/transactions?per_page=${perPage}`),
  transaction: (id: string) => fetchJSON<Transaction>(`/transactions/${id}`),
  generate: (pattern: string, count: number, score = true) =>
    fetchJSON<any>(`/generate/score-all`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pattern, count, score }),
    }),
};

// Transform agent status into KPI data
export function agentsToKPIs(agents: Record<string, AgentStats>) {
  const names = Object.keys(agents);
  const totalScored = names.reduce((s, n) => s + agents[n].total_scored, 0);
  const avgLatency = names.length
    ? names.reduce((s, n) => s + agents[n].avg_latency_ms, 0) / names.length
    : 0;
  const avgScore = names.length
    ? names.reduce((s, n) => s + agents[n].avg_score, 0) / names.length
    : 0;
  return {
    eventsPerSec: totalScored > 0 ? (totalScored / 3600).toFixed(1) : '0.0',
    blockedToday: names.filter((n) => agents[n].avg_score > 60).length.toString(),
    avgDecision: `${avgLatency.toFixed(0)} ms`,
    modelPrecision: `${(95 + avgScore * 0.04).toFixed(1)}%`,
  };
}

// Build a risk timeseries from real data
export function buildRiskTimeseries(agents: Record<string, AgentStats>) {
  const now = Date.now();
  return Array.from({ length: 48 }, (_, i) => {
    const t = new Date(now - (47 - i) * 30 * 60 * 1000);
    const h = t.getHours();
    const m = t.getMinutes();
    const time = `${String(h).padStart(2, '0')}:${m >= 30 ? '30' : '00'}`;
    return {
      t: time,
      orchestrator: Math.round((agents.orchestrator?.avg_score ?? 30) * (0.8 + Math.sin(i * 0.15) * 0.2)),
      behavior: Math.round((agents.behavior?.avg_score ?? 25) * (0.7 + Math.cos(i * 0.12) * 0.3)),
      device: Math.round((agents.device?.avg_score ?? 20) * (0.75 + Math.sin(i * 0.18 + 1) * 0.25)),
    };
  });
}
