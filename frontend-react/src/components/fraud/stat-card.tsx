import { motion } from "motion/react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

export function StatCard({
  label,
  value,
  delta,
  positive,
  index = 0,
}: {
  label: string;
  value: string;
  delta: string;
  positive: boolean;
  index?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="surface-card relative overflow-hidden p-4 scanline scanline-after"
    >
      <div className="flex items-start justify-between">
        <span className="font-mono-tech text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          {label}
        </span>
        <span
          className={`flex items-center gap-0.5 font-mono-tech text-[10px] ${
            positive ? "text-[color:var(--success)]" : "text-[color:var(--danger)]"
          }`}
        >
          {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
          {delta}
        </span>
      </div>
      <div className="mt-3 font-display text-2xl font-semibold tabular-nums">{value}</div>
      <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-muted">
        <div className="h-full w-1/2 shimmer-bar" />
      </div>
    </motion.div>
  );
}
