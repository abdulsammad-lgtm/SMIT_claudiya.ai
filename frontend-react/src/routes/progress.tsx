import { createFileRoute } from "@tanstack/react-router";
import { TopBar } from "@/components/topbar";
import { AgentProgress } from "@/components/fraud/agent-progress";
import { AUDIT_EVENTS } from "@/lib/fraud-data";
import { motion, AnimatePresence } from "motion/react";
import { useAgentsStatus, useTransactions } from "@/hooks/use-fraud-data";
import { X, AlertCircle, Fingerprint, GitBranch, Brain } from "lucide-react";
import { useState } from "react";

export const Route = createFileRoute("/progress")({
  head: () => ({
    meta: [
      { title: "Agent Progress — Claudiya.ai" },
      { name: "description", content: "Live progress of orchestrator, behavior, and device fraud detection agents." },
    ],
  }),
  component: ProgressPage,
});

const ACTOR_ICON: Record<string, typeof GitBranch> = {
  orchestrator: GitBranch,
  behavior: Brain,
  device: Fingerprint,
};

function ProgressPage() {
  const { data: agentsData } = useAgentsStatus();
  const { data: txnsData } = useTransactions(20);
  const [selected, setSelected] = useState<number | null>(null);

  const agentList = agentsData?.agents
    ? Object.entries(agentsData.agents).map(([id, a]) => ({ id, ...a }))
    : [];

  const events = txnsData?.transactions?.slice(0, 8).map((t) => ({
    ts: t.timestamp ? new Date(t.timestamp).toLocaleTimeString() : "--",
    actor: t.decision === "decline" ? "orchestrator" : t.risk_score && t.risk_score > 60 ? "behavior" : "device",
    msg: `Score ${t.risk_score?.toFixed(0)} · ${t.customer_id} · ${t.decision ?? "pending"}`,
    detail: `Amount: $${t.amount.toFixed(2)} · Risk: ${t.risk_score?.toFixed(0) ?? "N/A"} · Decision: ${t.decision ?? "pending"} · ${t.payment_method ?? "N/A"}`,
  })) ?? AUDIT_EVENTS.slice(0, 8).map((e) => ({ ...e, detail: `Event recorded at ${e.ts} by ${e.actor}. ${e.msg}` }));

  return (
    <>
      <TopBar title="Agent Progress" subtitle="pipeline · live" />
      <main className="flex-1 p-4 lg:p-6 space-y-6">
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="surface-card relative overflow-hidden p-6"
        >
          <div className="absolute inset-0 grid-bg opacity-30" />
          <div className="relative">
            <span className="font-mono-tech text-[10px] uppercase tracking-[0.22em] text-primary">
              pipeline observability
            </span>
            <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight">
              Per-agent execution graph
            </h1>
            <p className="mt-2 max-w-xl text-sm text-muted-foreground">
              Each agent runs a deterministic four-stage pipeline. Stage timings are streamed in real-time and
              gated by the guardrails defined on the corresponding agent page.
            </p>
          </div>
        </motion.section>

        <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
          <AgentProgress agentData={agentList} />

          <div className="surface-card p-5">
            <div className="flex items-center justify-between">
              <h3 className="font-display text-sm font-semibold">Coordination log</h3>
              <span className="font-mono-tech text-[10px] uppercase tracking-wider text-[color:var(--success)]">
                streaming
              </span>
            </div>
            <p className="mt-1 font-mono-tech text-[9px] uppercase tracking-wider text-muted-foreground">click an entry to inspect</p>
            <ol className="mt-3 space-y-2 font-mono-tech text-xs">
              {events.map((e, i) => {
                const Icon = ACTOR_ICON[e.actor] ?? AlertCircle;
                return (
                  <motion.li
                    key={i}
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    onClick={() => setSelected(i)}
                    className="grid cursor-pointer grid-cols-[auto_60px_92px_1fr] items-center gap-2 rounded-md border-l-2 border-primary/40 px-3 py-2 hover:bg-accent/40 transition"
                  >
                    <Icon className="h-3.5 w-3.5 text-primary shrink-0" />
                    <span className="text-muted-foreground">{e.ts}</span>
                    <span className="uppercase tracking-wider text-primary">{e.actor}</span>
                    <span className="text-foreground/90 truncate">{e.msg}</span>
                  </motion.li>
                );
              })}
            </ol>
          </div>
        </div>

        <AnimatePresence>
          {selected !== null && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelected(null)}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 10 }}
                onClick={(e) => e.stopPropagation()}
                className="surface-card relative w-full max-w-lg rounded-xl border border-border/60 p-6 shadow-xl"
              >
                <button
                  onClick={() => setSelected(null)}
                  className="absolute right-4 top-4 rounded-md p-1 hover:bg-accent transition"
                >
                  <X className="h-4 w-4" />
                </button>
                <div className="flex items-center gap-3">
                  <div className="grid h-10 w-10 place-items-center rounded-md bg-primary/10 ring-1 ring-primary/30">
                    <AlertCircle className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-display text-base font-semibold">Audit event detail</h3>
                    <p className="font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
                      {events[selected]?.actor} · {events[selected]?.ts}
                    </p>
                  </div>
                </div>
                <div className="mt-5 space-y-3 rounded-md border border-border/60 bg-card/60 p-4">
                  <div className="flex justify-between font-mono-tech text-xs">
                    <span className="text-muted-foreground">Actor</span>
                    <span className="text-foreground">{events[selected]?.actor}</span>
                  </div>
                  <div className="flex justify-between font-mono-tech text-xs">
                    <span className="text-muted-foreground">Timestamp</span>
                    <span className="text-foreground">{events[selected]?.ts}</span>
                  </div>
                  <div className="flex justify-between font-mono-tech text-xs">
                    <span className="text-muted-foreground">Message</span>
                    <span className="text-foreground text-right max-w-[260px]">{events[selected]?.msg}</span>
                  </div>
                  <div className="border-t border-border/40 pt-3">
                    <p className="font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Details</p>
                    <p className="font-mono-tech text-xs text-foreground/80">{events[selected]?.detail}</p>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </>
  );
}
