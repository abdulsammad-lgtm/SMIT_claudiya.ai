import { motion } from "motion/react";
import { GUARDRAILS, type AgentId } from "@/lib/fraud-data";
import { Lock, ShieldCheck } from "lucide-react";

export function Guardrails({ agent }: { agent: AgentId }) {
  const items = GUARDRAILS[agent];
  return (
    <div className="surface-card p-5">
      <div className="flex items-center gap-2">
        <Lock className="h-4 w-4 text-primary" />
        <h3 className="font-display text-sm font-semibold">Guardrails</h3>
        <span className="ml-auto font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
          {items.filter((i) => i.status === "active").length}/{items.length} enforced
        </span>
      </div>
      <ul className="mt-4 space-y-2.5">
        {items.map((g, i) => (
          <motion.li
            key={g.title}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="grid grid-cols-[auto_1fr_auto] items-start gap-3 rounded-md border border-border/60 bg-card/60 p-3"
          >
            <div
              className={`mt-0.5 grid h-7 w-7 place-items-center rounded-md ring-1 ${
                g.status === "active"
                  ? "bg-[color:var(--success)]/15 ring-[color:var(--success)]/40"
                  : "bg-muted ring-border"
              }`}
            >
              <ShieldCheck
                className={`h-3.5 w-3.5 ${
                  g.status === "active" ? "text-[color:var(--success)]" : "text-muted-foreground"
                }`}
              />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium">{g.title}</p>
              <p className="text-xs text-muted-foreground">{g.detail}</p>
            </div>
            <span
              className={`font-mono-tech text-[10px] uppercase tracking-wider ${
                g.status === "active" ? "text-[color:var(--success)]" : "text-muted-foreground"
              }`}
            >
              {g.status}
            </span>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}
