import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { AGENTS, type AgentId } from "@/lib/fraud-data";
import type { AgentStats } from "@/lib/api";
import { Activity, GitBranch, Brain, Fingerprint, BarChart3 } from "lucide-react";

const ICON: Record<AgentId, typeof Activity> = {
  orchestrator: GitBranch,
  behavior: Brain,
  device: Fingerprint,
};

const AGENT_KEYS: Record<string, AgentId> = {
  device: "device",
  behavior: "behavior",
  network: "orchestrator",
  transaction: "orchestrator",
  behavioral: "orchestrator",
};

export function AgentProgress({ compact = false, agentData }: { compact?: boolean; agentData?: { id: string; avg_score: number; avg_latency_ms: number; total_scored: number }[] }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick((x) => x + 1), 1400);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="grid gap-3">
      {AGENTS.map((agent, ai) => {
        const Icon = ICON[agent.id];
        const activeStep = (tick + ai) % agent.pipeline.length;
        const totalDone = agent.pipeline.slice(0, activeStep + 1).reduce((a, b) => a + b.weight, 0);

        // Find matching real agent data
        const realData = agentData?.find((a) => AGENT_KEYS[a.id] === agent.id || a.id === agent.id);
        const realScore = realData?.avg_score ?? null;
        const realLatency = realData?.avg_latency_ms ?? null;

        return (
          <motion.div
            key={agent.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: ai * 0.08, duration: 0.4 }}
            className="surface-card p-4"
          >
            <div className="flex items-center gap-3">
              <div className="relative grid h-10 w-10 place-items-center rounded-md bg-card ring-1 ring-border">
                <Icon className={`h-4.5 w-4.5 ${agent.accent}`} />
                <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-[color:var(--success)] ring-2 ring-card pulse-dot" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="font-display text-sm font-semibold truncate">{agent.name}</h4>
                  <span className="font-mono-tech text-[10px] uppercase tracking-wider text-[color:var(--success)]">online</span>
                </div>
                <p className="font-mono-tech text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{agent.tagline}</p>
              </div>
              <div className="flex items-center gap-3 font-mono-tech text-xs">
                {realScore !== null && (
                  <span className="tabular-nums text-primary flex items-center gap-1">
                    <BarChart3 className="h-3 w-3 text-muted-foreground" />
                    {realScore.toFixed(0)}
                  </span>
                )}
                <span className="text-muted-foreground tabular-nums">{totalDone}%</span>
              </div>
            </div>

            {/* Pipeline */}
            <div className="mt-3 flex items-center gap-1.5">
              {agent.pipeline.map((step, i) => {
                const isActive = i === activeStep;
                const isDone = i < activeStep;
                return (
                  <div key={step.label} className="flex-1">
                    <div className={`h-1.5 rounded-full overflow-hidden ${isDone ? "bg-[color:var(--success)]/60" : "bg-muted"}`}>
                      {isActive && (
                        <motion.div
                          key={tick}
                          initial={{ width: "0%" }}
                          animate={{ width: "100%" }}
                          transition={{ duration: 1.3, ease: "linear" }}
                          className="h-full bg-[var(--gradient-primary)]"
                        />
                      )}
                    </div>
                    {!compact && (
                      <p className={`mt-1.5 font-mono-tech text-[9px] uppercase tracking-wider truncate ${isActive ? "text-foreground" : "text-muted-foreground"}`}>
                        {step.label}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Real-time metrics row */}
            {realData && !compact && (
              <div className="mt-2 flex gap-4 font-mono-tech text-[10px] text-muted-foreground">
                <span>Score: <span className="text-primary">{realScore?.toFixed(1)}</span></span>
                <span>Latency: <span className="text-primary">{realLatency?.toFixed(0)}ms</span></span>
                <span>Scored: <span className="text-primary">{realData.total_scored}</span></span>
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
