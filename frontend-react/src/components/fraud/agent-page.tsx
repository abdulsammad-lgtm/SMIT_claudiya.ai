import { motion } from "motion/react";
import { AGENTS, type AgentId } from "@/lib/fraud-data";
import { Guardrails } from "./guardrails";
import { AgentExtras } from "./agent-extras";
import { useAgentsStatus, useTransactions } from "@/hooks/use-fraud-data";
import type { AgentStats } from "@/lib/api";
import { Cpu, Gauge, Layers, Network, Activity, Clock, BarChart3, Shield } from "lucide-react";

export function AgentPage({ id }: { id: AgentId }) {
  const agent = AGENTS.find((a) => a.id === id)!;
  const { data: agentsData } = useAgentsStatus();
  const { data: txnsData } = useTransactions(20);

  const realStats: AgentStats | undefined = agentsData?.agents ? Object.entries(agentsData.agents).find(([k]) => k === id || (id === "orchestrator" && ["network", "transaction", "behavioral"].includes(k)))?.[1] : undefined;

  // Build metrics from real data
  const metrics = realStats ? [
    { label: "Avg Score", value: realStats.avg_score.toFixed(1), icon: Activity },
    { label: "Latency", value: `${realStats.avg_latency_ms.toFixed(0)} ms`, icon: Clock },
    { label: "Total Scored", value: realStats.total_scored.toString(), icon: BarChart3 },
    { label: "Weight", value: `${(realStats.weight * 100).toFixed(0)}%`, icon: Shield },
  ] : [
    { label: "Decisions / min", value: id === "orchestrator" ? "8,412" : id === "behavior" ? "1.2M" : "8.4M", icon: Gauge },
    { label: "Active rules", value: id === "orchestrator" ? "47 rules" : id === "behavior" ? "184 dims" : "62 bits", icon: Layers },
    { label: "Avg latency", value: id === "orchestrator" ? "31 ms" : id === "behavior" ? "12 ms" : "8 ms", icon: Cpu },
    { label: "Coverage", value: id === "orchestrator" ? "3.2 / event" : id === "behavior" ? "96.3%" : "99.1%", icon: Network },
  ];

  const events = txnsData?.transactions?.slice(0, 6).map((t) => ({
    ts: t.timestamp ? new Date(t.timestamp).toLocaleTimeString() : "--",
    actor: id,
    msg: `Score ${t.risk_score?.toFixed(0)} · ${t.customer_id} · ${t.decision ?? "pending"}`,
  })) ?? [];

  return (
    <div className="grid gap-5">
      {/* Hero */}
      <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="surface-card relative overflow-hidden p-6">
        <div className="absolute inset-0 grid-bg opacity-40" />
        <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-[var(--gradient-primary)] opacity-20 blur-3xl" />
        <div className="relative flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="font-mono-tech text-[10px] uppercase tracking-[0.22em] text-primary">Agent · {id}</span>
            <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight">{agent.name}</h1>
            <p className="mt-2 max-w-xl text-sm text-muted-foreground">{agent.description}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-2 surface-card px-3 py-1.5">
              <span className="relative flex h-2 w-2">
                <span className="absolute inset-0 rounded-full bg-[color:var(--success)] opacity-60 pulse-dot" />
                <span className="relative h-2 w-2 rounded-full bg-[color:var(--success)]" />
              </span>
              <span className="font-mono-tech text-[10px] uppercase tracking-wider">{realStats ? "Online" : "Healthy"}</span>
            </span>
            {realStats && (
              <span className="surface-card px-3 py-1.5 font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
                weight: {(realStats.weight * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </div>
      </motion.section>

      {/* Metrics */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((m, i) => (
          <motion.div key={m.label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} className="surface-card p-4">
            <div className="flex items-center gap-2">
              <m.icon className="h-3.5 w-3.5 text-primary" />
              <span className="font-mono-tech text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{m.label}</span>
            </div>
            <p className="mt-2 font-display text-xl font-semibold tabular-nums">{m.value}</p>
          </motion.div>
        ))}
      </div>

      <AgentExtras id={id} />

      <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
        <Guardrails agent={id} />

        {/* Agent trace */}
        <div className="surface-card p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-sm font-semibold">Agent trace</h3>
            <span className="font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">last {events.length} events</span>
          </div>
          <ol className="mt-4 space-y-2 font-mono-tech text-xs">
            {events.length > 0 ? events.map((e, i) => (
              <motion.li key={i} initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }} className="grid grid-cols-[64px_90px_1fr] gap-2 border-l-2 border-primary/40 pl-3">
                <span className="text-muted-foreground">{e.ts}</span>
                <span className="uppercase tracking-wider text-primary">{e.actor}</span>
                <span className="text-foreground/90">{e.msg}</span>
              </motion.li>
            )) : (
              <li className="text-muted-foreground text-xs pl-3">No recent events. Generate data to populate the trace.</li>
            )}
          </ol>
        </div>
      </div>
    </div>
  );
}
