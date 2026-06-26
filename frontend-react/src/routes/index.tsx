import { useDashboardData } from "@/hooks/use-fraud-data";
import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { TopBar } from "@/components/topbar";
import { StatCard } from "@/components/fraud/stat-card";
import { RiskChart } from "@/components/fraud/risk-chart";
import { ThreatFeed } from "@/components/fraud/threat-feed";
import { AgentProgress } from "@/components/fraud/agent-progress";
import { Activity, Globe2, Zap, BarChart3, Shield, Clock } from "lucide-react";
import { useState } from "react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — Claudiya.ai" },
      { name: "description", content: "Real-time fraud detection dashboard powered by multi-agent AI." },
    ],
  }),
  component: Dashboard,
});

const REGIONS = [
  { name: "Americas", load: 72, risk: "low" },
  { name: "EMEA", load: 64, risk: "med" },
  { name: "APAC", load: 51, risk: "low" },
  { name: "LATAM", load: 38, risk: "high" },
];

function Dashboard() {
  const { kpis, stats, txns, agentList, loading } = useDashboardData();
  const [searchQuery, setSearchQuery] = useState("");

  const allTxns = txns.data?.transactions ?? [];
  const filteredTxns = searchQuery
    ? allTxns.filter((t) =>
        [t.order_id, t.customer_id, t.decision, t.currency, t.payment_method, String(t.amount)]
          .some((f) => f?.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : allTxns;

  const kpiCards = [
    { label: "Events / sec", value: kpis.eventsPerSec, delta: `from ${stats.data?.total ?? 0} scored`, positive: true },
    { label: "Blocked today", value: kpis.blockedToday, delta: "flagged", positive: false },
    { label: "Avg decision", value: kpis.avgDecision, delta: "p95 latency", positive: true },
    { label: "Model precision", value: kpis.modelPrecision, delta: "across all agents", positive: true },
  ];

  const c = stats.data?.counts ?? { approve: 0, review: 0, decline: 0, pending: 0 };

  return (
    <>
      <TopBar title="Operations Dashboard" subtitle="claudiya · live" onSearchChange={setSearchQuery} />
      <main className="flex-1 p-4 lg:p-6 space-y-6">
        {/* Hero strip */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="surface-card relative overflow-hidden p-6"
        >
          <div className="absolute inset-0 grid-bg opacity-30" />
          <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-[var(--gradient-primary)] opacity-25 blur-3xl" />
          <div className="relative grid gap-6 lg:grid-cols-[1.4fr_1fr] lg:items-end">
            <div>
              <div className="flex items-center gap-2">
                <span className="flex h-2 w-2 rounded-full bg-[color:var(--success)] pulse-dot" />
                <span className="font-mono-tech text-[10px] uppercase tracking-[0.22em] text-[color:var(--success)]">
                  all agents online · {loading ? "loading..." : `${stats.data?.total ?? 0} transactions scored`}
                </span>
              </div>
              <h1 className="mt-3 font-display text-3xl lg:text-4xl font-semibold tracking-tight">
                Three agents. One verdict.
                <br />
                <span className="text-gradient-primary">Zero blind spots.</span>
              </h1>
              <p className="mt-3 max-w-xl text-sm text-muted-foreground">
                Claudiya.ai fuses behavioural telemetry, device intelligence and policy orchestration into a single
                sub-100ms decision pipeline — with hard guardrails on every action.
              </p>
              <div className="mt-4 flex flex-wrap gap-2 font-mono-tech text-[11px]">
                <span className="surface-card px-3 py-1.5"><Zap className="inline h-3 w-3 mr-1 text-primary" />{kpis.avgDecision} p95</span>
                <span className="surface-card px-3 py-1.5"><BarChart3 className="inline h-3 w-3 mr-1 text-primary" />{c.review ?? 0} review</span>
                <span className="surface-card px-3 py-1.5"><Shield className="inline h-3 w-3 mr-1 text-primary" />{c.approve ?? 0} approved</span>
                <span className="surface-card px-3 py-1.5"><Clock className="inline h-3 w-3 mr-1 text-primary" />{c.pending ?? 0} pending</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {REGIONS.map((r, i) => (
                <motion.div
                  key={r.name}
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.1 + i * 0.05 }}
                  className="rounded-md border border-border/70 bg-card/60 p-3"
                >
                  <div className="flex items-center justify-between text-[10px] font-mono-tech uppercase tracking-wider">
                    <span className="text-muted-foreground">{r.name}</span>
                    <span className={r.risk === "high" ? "text-[color:var(--danger)]" : r.risk === "med" ? "text-[color:var(--warning)]" : "text-[color:var(--success)]"}>{r.risk}</span>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${r.load}%` }}
                      transition={{ delay: 0.3 + i * 0.06, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                      className="h-full bg-[var(--gradient-primary)]"
                    />
                  </div>
                  <p className="mt-1 font-mono-tech text-[10px] tabular-nums text-muted-foreground">{r.load}% capacity</p>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.section>

        {/* KPI strip */}
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {kpiCards.map((k, i) => <StatCard key={k.label} {...k} index={i} />)}
        </section>

        {/* Chart + threats */}
        <section className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
          <div className="surface-card p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-sm font-semibold">Risk surface · last 24h</h3>
                <p className="font-mono-tech text-[10px] uppercase tracking-[0.18em] text-muted-foreground">fused score from all agents</p>
              </div>
              <div className="flex items-center gap-3 font-mono-tech text-[10px]">
                <Legend color="oklch(0.82 0.16 195)" label="Orchestrator" />
                <Legend color="oklch(0.78 0.17 158)" label="Behavior" />
                <Legend color="oklch(0.74 0.14 240)" label="Device" />
              </div>
            </div>
            <div className="mt-2"><RiskChart /></div>
          </div>

          <ThreatFeed transactions={filteredTxns} />
        </section>

        {/* Agent progress */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h3 className="font-display text-sm font-semibold">Agent progress</h3>
              <p className="font-mono-tech text-[10px] uppercase tracking-[0.18em] text-muted-foreground">live pipeline status</p>
            </div>
          </div>
          <AgentProgress agentData={agentList} />
        </section>
      </main>
    </>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 uppercase tracking-wider text-muted-foreground">
      <span className="h-2 w-2 rounded-full" style={{ background: color }} />{label}
    </span>
  );
}
