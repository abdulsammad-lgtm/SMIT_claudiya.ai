import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { TopBar } from "@/components/topbar";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { useAgentsStatus, useStats, useTransactions } from "@/hooks/use-fraud-data";
import { api } from "@/lib/api";
import { ShieldCheck, Users, Sliders, Lock, Cpu, Activity, Clock, BarChart3, Play, Database, Loader2 } from "lucide-react";
import { useState } from "react";

export const Route = createFileRoute("/_authenticated/admin")({
  head: () => ({
    meta: [
      { title: "Admin Panel — Claudiya.ai" },
      { name: "description", content: "Manage policies, users and global guardrails." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: AdminPage,
});

const AGENT_COLORS: Record<string, string> = {
  device: "var(--info)",
  behavior: "var(--success)",
  network: "var(--warning)",
  transaction: "var(--primary)",
  behavioral: "var(--danger)",
};

const AGENT_LABELS: Record<string, string> = {
  device: "Device Intel",
  behavior: "Behavior Analysis",
  network: "Network Graph",
  transaction: "Transaction Scorer",
  behavioral: "Behavioral Bio",
};

const PATTERNS = [
  { value: "clean", label: "Clean transactions" },
  { value: "card_testing", label: "Card testing burst" },
  { value: "cod_fraud", label: "COD fraud ring" },
  { value: "friendly_fraud", label: "Friendly fraud" },
];

function AdminPage() {
  const { data: agentsData } = useAgentsStatus();
  const { data: statsData } = useStats();
  const { data: txnsData } = useTransactions(30);
  const [genPattern, setGenPattern] = useState("clean");
  const [genCount, setGenCount] = useState(10);
  const [genLoading, setGenLoading] = useState(false);
  const [genResult, setGenResult] = useState<string | null>(null);

  const agents = agentsData?.agents ?? {};
  const c = statsData?.counts ?? { approve: 0, review: 0, decline: 0, pending: 0 };
  const totalScored = Object.values(agents).reduce((s, a) => s + a.total_scored, 0);

  async function handleGenerate(score: boolean) {
    setGenLoading(true);
    setGenResult(null);
    try {
      const res = await api.generate(genPattern, genCount, score);
      setGenResult(`Generated ${res.inserted ?? res.count ?? "?"} transactions (pattern: ${genPattern})`);
    } catch (e: any) {
      setGenResult(`Error: ${e.message}`);
    }
    setGenLoading(false);
  }

  return (
    <>
      <TopBar title="Admin Panel" subtitle="governance · live" />
      <main className="flex-1 p-4 lg:p-6 space-y-6">
        <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="surface-card relative overflow-hidden p-6">
          <div className="absolute inset-0 grid-bg opacity-30" />
          <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-[var(--gradient-primary)] opacity-20 blur-3xl" />
          <div className="relative flex flex-wrap items-end justify-between gap-3">
            <div>
              <span className="font-mono-tech text-[10px] uppercase tracking-[0.22em] text-primary">admin · console</span>
              <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight">Governance & policy control</h1>
              <p className="mt-2 max-w-xl text-sm text-muted-foreground">Manage policies, agent thresholds, team access, and global guardrails. Every change is audited.</p>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              <Stat icon={Users} value={totalScored.toString()} label="Scored" />
              <Stat icon={Sliders} value={Object.keys(agents).length.toString()} label="Agents" />
              <Stat icon={BarChart3} value={(c.review + c.approve + c.decline).toString()} label="Decisions" />
            </div>
          </div>
        </motion.section>

        {/* Agent Status */}
        <section className="surface-card overflow-hidden">
          <div className="flex items-center justify-between border-b border-border/60 px-5 py-4">
            <div>
              <h3 className="font-display text-sm font-semibold">Agent health</h3>
              <p className="font-mono-tech text-[10px] uppercase tracking-[0.18em] text-muted-foreground">live status from pipeline</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
                  <th className="px-5 py-3">Agent</th>
                  <th className="px-3 py-3">Score</th>
                  <th className="px-3 py-3">Latency</th>
                  <th className="px-3 py-3">Scored</th>
                  <th className="px-3 py-3">Weight</th>
                  <th className="px-5 py-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(agents).map(([name, a], i) => (
                  <motion.tr key={name} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }} className="border-t border-border/40 hover:bg-accent/30">
                    <td className="px-5 py-3 font-medium" style={{ color: AGENT_COLORS[name] ?? "var(--primary)" }}>{AGENT_LABELS[name] ?? name}</td>
                    <td className="px-3 py-3 font-mono-tech text-xs">{a.avg_score.toFixed(1)}</td>
                    <td className="px-3 py-3 font-mono-tech text-xs text-muted-foreground">{a.avg_latency_ms.toFixed(0)}ms</td>
                    <td className="px-3 py-3 font-mono-tech text-xs text-muted-foreground">{a.total_scored}</td>
                    <td className="px-3 py-3">{(a.weight * 100).toFixed(0)}%</td>
                    <td className="px-5 py-3 text-right"><span className="text-[color:var(--success)] font-mono-tech text-[10px] uppercase tracking-wider">online</span></td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Data Generation */}
        <section className="surface-card p-5">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-primary" />
            <h3 className="font-display text-sm font-semibold">Data generation</h3>
          </div>
          <p className="mt-1 font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
            Generate sample transactions and score them through the full pipeline
          </p>
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <div className="flex flex-col gap-1">
              <label className="font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">Pattern</label>
              <select
                value={genPattern}
                onChange={(e) => setGenPattern(e.target.value)}
                className="h-9 rounded-md border border-border/60 bg-card px-3 font-mono-tech text-xs text-foreground outline-none focus:ring-1 focus:ring-primary"
              >
                {PATTERNS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">Count</label>
              <input
                type="number"
                min={1}
                max={100}
                value={genCount}
                onChange={(e) => setGenCount(Math.min(100, Math.max(1, Number(e.target.value))))}
                className="h-9 w-20 rounded-md border border-border/60 bg-card px-3 font-mono-tech text-xs text-foreground outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <button
              onClick={() => handleGenerate(false)}
              disabled={genLoading}
              className="flex h-9 items-center gap-1.5 rounded-md bg-primary px-4 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition"
            >
              {genLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Database className="h-3.5 w-3.5" />}
              Generate
            </button>
            <button
              onClick={() => handleGenerate(true)}
              disabled={genLoading}
              className="flex h-9 items-center gap-1.5 rounded-md border border-primary/40 bg-primary/10 px-4 text-xs font-medium text-primary hover:bg-primary/20 disabled:opacity-50 transition"
            >
              {genLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              Generate & Score
            </button>
          </div>
          {genResult && (
            <motion.p
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-3 font-mono-tech text-xs text-muted-foreground"
            >
              {genResult}
            </motion.p>
          )}
        </section>

        {/* Policies */}
        <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
          <div className="surface-card p-5">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" />
              <h3 className="font-display text-sm font-semibold">Global guardrails</h3>
            </div>
            <div className="mt-4 space-y-3">
              <Guardrail label="Require 2-agent consensus for blocks" enabled canToggle={false} />
              <Guardrail label="Max auto-block rate per 5min" value="0.8%" enabled canToggle={false} />
              <Guardrail label="Manual review threshold" value="$10,000" enabled canToggle={false} />
              <Guardrail label="PII redaction in logs" enabled canToggle={false} />
              <Guardrail label="Shadow mode for new policies (72h)" enabled canToggle={false} />
              <Guardrail label="Bias delta cap across cohorts" value="±15%" enabled canToggle={false} />
              <Guardrail label="Allow silent block on rooted devices" enabled={false} canToggle={false} />
            </div>
          </div>

          <div className="surface-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-border/60 px-5 py-4">
              <h3 className="font-display text-sm font-semibold">Recent transactions</h3>
            </div>
            <ul className="divide-y divide-border/40">
              {(txnsData?.transactions ?? []).slice(0, 5).map((t, i) => (
                <motion.li key={t.order_id} initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }} className="grid grid-cols-[1fr_auto] items-center gap-3 px-5 py-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-mono-tech">{t.order_id}</p>
                      <Badge variant="secondary" className="font-mono-tech text-[9px]">{t.decision || "pending"}</Badge>
                    </div>
                    <p className="truncate text-xs text-muted-foreground">{t.customer_id} · ${t.amount.toFixed(2)}</p>
                  </div>
                  <span className="font-mono-tech text-[11px] tabular-nums" style={{ color: t.risk_score != null && t.risk_score > 60 ? "var(--warning)" : "var(--success)" }}>
                    {t.risk_score?.toFixed(0) ?? "--"}
                  </span>
                </motion.li>
              ))}
              {(!txnsData?.transactions || txnsData.transactions.length === 0) && (
                <li className="px-5 py-8 text-center text-sm text-muted-foreground">No transactions yet. Generate data from the FastAPI backend.</li>
              )}
            </ul>
          </div>
        </div>
      </main>
    </>
  );
}

function Stat({ icon: Icon, value, label }: { icon: typeof Sliders; value: string; label: string }) {
  return (
    <div className="surface-card px-4 py-2.5">
      <Icon className="mx-auto h-3.5 w-3.5 text-primary" />
      <div className="mt-1 font-display text-lg font-semibold tabular-nums">{value}</div>
      <div className="font-mono-tech text-[9px] uppercase tracking-wider text-muted-foreground">{label}</div>
    </div>
  );
}

function Guardrail({ label, value, enabled, canToggle }: { label: string; value?: string; enabled: boolean; canToggle: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border/60 bg-card/60 px-3 py-2.5">
      <div className="min-w-0">
        <p className="text-sm">{label}</p>
        {value && <p className="font-mono-tech text-xs text-muted-foreground">{value}</p>}
      </div>
      <Switch defaultChecked={enabled} disabled={!canToggle} />
    </div>
  );
}
