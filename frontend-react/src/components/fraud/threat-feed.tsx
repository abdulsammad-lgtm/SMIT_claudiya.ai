import { motion } from "motion/react";
import { THREATS, type Severity } from "@/lib/fraud-data";
import { useEffect, useState } from "react";
import { ShieldAlert, ShieldCheck, ShieldQuestion, AlertOctagon, AlertCircle } from "lucide-react";
import type { Transaction } from "@/lib/api";

const SEV_STYLES: Record<Severity, { bg: string; ring: string; label: string }> = {
  low: { bg: "bg-[color:var(--info)]/15", ring: "ring-[color:var(--info)]/40", label: "text-[color:var(--info)]" },
  medium: { bg: "bg-[color:var(--warning)]/15", ring: "ring-[color:var(--warning)]/40", label: "text-[color:var(--warning)]" },
  high: { bg: "bg-[color:var(--danger)]/15", ring: "ring-[color:var(--danger)]/40", label: "text-[color:var(--danger)]" },
  critical: { bg: "bg-[color:var(--danger)]/25", ring: "ring-[color:var(--danger)]/60", label: "text-[color:var(--danger)]" },
};

const ACTION_ICON = {
  allowed: ShieldCheck,
  review: ShieldQuestion,
  challenged: ShieldAlert,
  blocked: AlertOctagon,
  approve: ShieldCheck,
  decline: AlertOctagon,
  pending: AlertCircle,
};

export function ThreatFeed({ transactions }: { transactions?: Transaction[] }) {
  const [items, setItems] = useState(THREATS);

  useEffect(() => {
    if (transactions && transactions.length > 0) {
      // Map real transactions to threat-like items
      const mapped = transactions.slice(0, 7).map((t) => {
        const score = t.risk_score ?? 0;
        const sev: Severity = score > 80 ? "critical" : score > 60 ? "high" : score > 30 ? "medium" : "low";
        const action = t.decision === "approve" ? "allowed" : t.decision === "decline" ? "blocked" : t.decision === "review" ? "review" : "pending";
        return {
          id: t.order_id,
          ts: t.timestamp ? new Date(t.timestamp).toLocaleTimeString() : "--",
          account: t.customer_id,
          amount: `$${t.amount.toFixed(2)}`,
          country: "US",
          vector: `risk ${score.toFixed(0)}`,
          severity: sev,
          agent: "orchestrator" as const,
          action: action as "allowed" | "review" | "challenged" | "blocked",
        };
      });
      setItems(mapped);
    }
  }, [transactions]);

  return (
    <div className="surface-card overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
        <div>
          <h3 className="font-display text-sm font-semibold">Live threat feed</h3>
          <p className="font-mono-tech text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            real-time · {transactions?.length ?? 0} transactions
          </p>
        </div>
        <span className="flex items-center gap-1.5 font-mono-tech text-[10px] uppercase tracking-wider text-[color:var(--success)]">
          <span className="relative flex h-2 w-2">
            <span className="absolute inset-0 rounded-full bg-[color:var(--success)] opacity-60 pulse-dot" />
            <span className="relative h-2 w-2 rounded-full bg-[color:var(--success)]" />
          </span>
          streaming
        </span>
      </div>

      <ul className="divide-y divide-border/40">
        {items.slice(0, 7).map((t, i) => {
          const sev = SEV_STYLES[t.severity];
          const Icon = ACTION_ICON[t.action] || ShieldQuestion;
          return (
            <motion.li
              key={t.id}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: i * 0.03 }}
              className="grid grid-cols-[auto_1fr_auto] items-center gap-3 px-4 py-2.5 hover:bg-accent/40"
            >
              <div className={`grid h-8 w-8 place-items-center rounded-md ${sev.bg} ring-1 ${sev.ring}`}>
                <Icon className={`h-4 w-4 ${sev.label}`} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-mono-tech text-foreground">{t.id}</span>
                  <span className="font-mono-tech text-muted-foreground">{t.ts}</span>
                  <span className={`font-mono-tech uppercase tracking-wider text-[10px] ${sev.label}`}>{t.severity}</span>
                </div>
                <p className="truncate text-[12px] text-muted-foreground">
                  <span className="text-foreground">{t.amount}</span> · {t.country} · {t.vector}
                </p>
              </div>
              <span className="font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">{t.action}</span>
            </motion.li>
          );
        })}
      </ul>
    </div>
  );
}
