import { motion } from "motion/react";
import { useEffect, useState } from "react";
import {
  Fingerprint,
  Smartphone,
  Wifi,
  ShieldAlert,
  Activity,
  MousePointer2,
  Keyboard,
  Waves,
  Share2,
  Receipt,
  PieChart as PieIcon,
} from "lucide-react";
import type { AgentId } from "@/lib/fraud-data";

/* ---------------- shared ---------------- */
function PanelHeader({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
          <Icon className="h-3.5 w-3.5" />
        </span>
        <div>
          <h3 className="font-display text-sm font-semibold leading-tight">{title}</h3>
          <p className="font-mono-tech text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            {subtitle}
          </p>
        </div>
      </div>
      <span className="flex items-center gap-1.5 font-mono-tech text-[10px] uppercase tracking-wider text-[color:var(--success)]">
        <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--success)] pulse-dot" />
        live
      </span>
    </div>
  );
}

function Bar({ label, value, tone = "primary" }: { label: string; value: number; tone?: "primary" | "warn" | "danger" | "success" }) {
  const color =
    tone === "danger"
      ? "var(--danger)"
      : tone === "warn"
      ? "var(--warning)"
      : tone === "success"
      ? "var(--success)"
      : "var(--primary)";
  return (
    <div>
      <div className="flex items-center justify-between font-mono-tech text-[10px] uppercase tracking-wider">
        <span className="text-muted-foreground">{label}</span>
        <span className="tabular-nums" style={{ color: `oklch(from ${color} l c h)` }}>
          {value}%
        </span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          className="h-full"
          style={{ background: `linear-gradient(90deg, color-mix(in oklab, ${color} 60%, transparent), ${color})` }}
        />
      </div>
    </div>
  );
}

/* ---------------- Device Intel ---------------- */
function DeviceIntel() {
  const devices = [
    { id: "iOS 17.4 · iPhone15,3", trust: 92, country: "US", asn: "AS7922", flag: false },
    { id: "Android 14 · Pixel 8", trust: 81, country: "DE", asn: "AS3320", flag: false },
    { id: "Chrome 126 · Win11", trust: 58, country: "BR", asn: "AS28573", flag: true },
    { id: "Emulator · GenyMotion", trust: 12, country: "NG", asn: "AS37148", flag: true },
  ];
  return (
    <div className="surface-card p-5">
      <PanelHeader icon={Smartphone} title="Device Intel" subtitle="fingerprint · network · trust" />
      <div className="mt-4 grid grid-cols-3 gap-3">
        {[
          { label: "Entropy", value: "62.4 bits", icon: Fingerprint, color: "text-primary" },
          { label: "ASN reputation", value: "A-", icon: Wifi, color: "text-[color:var(--success)]" },
          { label: "Anomalies", value: "14", icon: ShieldAlert, color: "text-[color:var(--warning)]" },
        ].map((s) => (
          <div key={s.label} className="rounded-md border border-border/70 bg-card/60 p-3">
            <s.icon className={`h-3.5 w-3.5 ${s.color}`} />
            <p className="mt-2 font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
              {s.label}
            </p>
            <p className="font-display text-base font-semibold tabular-nums">{s.value}</p>
          </div>
        ))}
      </div>
      <ul className="mt-4 space-y-2">
        {devices.map((d, i) => (
          <motion.li
            key={d.id}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="grid grid-cols-[1fr_80px_60px] items-center gap-3 rounded-md border border-border/60 bg-card/40 px-3 py-2"
          >
            <div className="min-w-0">
              <p className="truncate font-mono-tech text-[11px] text-foreground/90">{d.id}</p>
              <p className="font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
                {d.country} · {d.asn}
              </p>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${d.trust}%` }}
                transition={{ delay: 0.2 + i * 0.05, duration: 0.7 }}
                className="h-full"
                style={{
                  background:
                    d.trust > 70
                      ? "var(--success)"
                      : d.trust > 40
                      ? "var(--warning)"
                      : "var(--danger)",
                }}
              />
            </div>
            <span
              className="font-mono-tech text-[10px] uppercase tracking-wider tabular-nums"
              style={{
                color:
                  d.trust > 70
                    ? "var(--success)"
                    : d.trust > 40
                    ? "var(--warning)"
                    : "var(--danger)",
              }}
            >
              {d.flag ? "FLAG" : "OK"} {d.trust}
            </span>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}

/* ---------------- Behavior Analysis ---------------- */
function BehaviorAnalysis() {
  // animated sparkline
  const points = Array.from({ length: 40 }, (_, i) => {
    const x = (i / 39) * 100;
    const y =
      40 +
      Math.sin(i * 0.5) * 14 +
      Math.cos(i * 0.21) * 6 +
      (i === 28 ? -22 : i === 29 ? -18 : 0);
    return [x, y] as const;
  });
  const path = points.map(([x, y], i) => `${i ? "L" : "M"}${x},${y}`).join(" ");
  const area = `${path} L100,80 L0,80 Z`;

  return (
    <div className="surface-card p-5">
      <PanelHeader icon={Activity} title="Behavior Analysis" subtitle="velocity · session diff · cohort" />
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {[
          { label: "Velocity σ", value: "+2.8", tone: "warn" as const },
          { label: "Session diff", value: "0.41", tone: "primary" as const },
          { label: "Cohort match", value: "94%", tone: "success" as const },
        ].map((s) => (
          <div key={s.label} className="rounded-md border border-border/70 bg-card/60 p-3">
            <p className="font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
              {s.label}
            </p>
            <p
              className="font-display text-lg font-semibold tabular-nums"
              style={{
                color:
                  s.tone === "warn"
                    ? "var(--warning)"
                    : s.tone === "success"
                    ? "var(--success)"
                    : "var(--primary)",
              }}
            >
              {s.value}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-md border border-border/60 bg-card/40 p-3">
        <div className="flex items-center justify-between font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
          <span>session 0x7a13 · velocity</span>
          <span>last 60s</span>
        </div>
        <svg viewBox="0 0 100 80" className="mt-2 h-28 w-full">
          <defs>
            <linearGradient id="beh-grad" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="oklch(0.78 0.17 158)" stopOpacity="0.45" />
              <stop offset="100%" stopColor="oklch(0.78 0.17 158)" stopOpacity="0" />
            </linearGradient>
          </defs>
          <motion.path
            d={area}
            fill="url(#beh-grad)"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8 }}
          />
          <motion.path
            d={path}
            fill="none"
            stroke="oklch(0.78 0.17 158)"
            strokeWidth="1.2"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.2, ease: "easeOut" }}
          />
          <motion.circle
            cx={points[28][0]}
            cy={points[28][1]}
            r="1.6"
            fill="oklch(0.7 0.2 25)"
            initial={{ scale: 0 }}
            animate={{ scale: [0, 1.6, 1] }}
            transition={{ delay: 1, duration: 0.6 }}
          />
        </svg>
      </div>

      <div className="mt-4 space-y-2">
        <Bar label="Typing rhythm" value={72} tone="success" />
        <Bar label="Navigation entropy" value={48} />
        <Bar label="Transaction velocity" value={86} tone="warn" />
      </div>
    </div>
  );
}

/* ---------------- Behavioral Biometrics ---------------- */
function BehavioralBio() {
  const [pulse, setPulse] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setPulse((p) => (p + 1) % 100), 90);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="surface-card p-5">
      <PanelHeader icon={Waves} title="Behavioral Biometrics" subtitle="keystroke · pointer · gesture" />
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-md border border-border/60 bg-card/40 p-3">
          <div className="flex items-center gap-2 font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
            <Keyboard className="h-3 w-3" /> keystroke dwell
          </div>
          <div className="mt-2 flex h-14 items-end gap-[3px]">
            {Array.from({ length: 28 }).map((_, i) => {
              const h = 20 + ((Math.sin(i * 0.7 + pulse * 0.05) + 1) / 2) * 60;
              return (
                <span
                  key={i}
                  className="flex-1 rounded-t-sm"
                  style={{
                    height: `${h}%`,
                    background: "linear-gradient(180deg, var(--primary), color-mix(in oklab, var(--primary) 20%, transparent))",
                    opacity: 0.55 + (i / 28) * 0.45,
                  }}
                />
              );
            })}
          </div>
          <p className="mt-2 font-mono-tech text-[10px] text-muted-foreground">
            avg 118ms · baseline 122ms · Δ 3.3%
          </p>
        </div>
        <div className="rounded-md border border-border/60 bg-card/40 p-3">
          <div className="flex items-center gap-2 font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
            <MousePointer2 className="h-3 w-3" /> pointer trajectory
          </div>
          <svg viewBox="0 0 100 60" className="mt-2 h-14 w-full">
            <motion.path
              d="M2,55 C20,10 35,52 50,28 C65,8 80,48 98,18"
              fill="none"
              stroke="var(--primary)"
              strokeWidth="1.2"
              strokeDasharray="2 3"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1.4, repeat: Infinity, repeatType: "reverse" }}
            />
            <circle cx="98" cy="18" r="1.6" fill="var(--primary)" />
          </svg>
          <p className="mt-2 font-mono-tech text-[10px] text-muted-foreground">
            jitter 0.21 · curvature 1.04 · match 0.92
          </p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2">
        {[
          { l: "Dwell", v: 92 },
          { l: "Flight", v: 88 },
          { l: "Pressure", v: 71 },
          { l: "Swipe arc", v: 84 },
          { l: "Gyro drift", v: 66 },
          { l: "Tilt", v: 79 },
        ].map((m) => (
          <div key={m.l} className="rounded-md border border-border/60 bg-card/40 px-2 py-1.5">
            <div className="flex items-center justify-between font-mono-tech text-[10px] uppercase tracking-wider">
              <span className="text-muted-foreground">{m.l}</span>
              <span className="tabular-nums text-primary">{m.v}</span>
            </div>
            <div className="mt-1 h-1 overflow-hidden rounded-full bg-muted">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${m.v}%` }}
                transition={{ duration: 1 }}
                className="h-full bg-[var(--gradient-primary)]"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------------- Network Graph ---------------- */
function NetworkGraph() {
  const nodes = [
    { id: "C", x: 50, y: 50, r: 6, tone: "primary", label: "Orchestrator" },
    { id: "n1", x: 18, y: 22, r: 3.5, tone: "success" },
    { id: "n2", x: 84, y: 26, r: 3.5, tone: "warn" },
    { id: "n3", x: 88, y: 70, r: 4.5, tone: "danger" },
    { id: "n4", x: 22, y: 78, r: 3, tone: "primary" },
    { id: "n5", x: 56, y: 16, r: 2.5, tone: "primary" },
    { id: "n6", x: 70, y: 86, r: 3, tone: "warn" },
    { id: "n7", x: 10, y: 52, r: 3, tone: "success" },
    { id: "n8", x: 38, y: 38, r: 2.5, tone: "primary" },
    { id: "n9", x: 64, y: 56, r: 3, tone: "danger" },
  ] as const;
  const color = (t: string) =>
    t === "danger"
      ? "var(--danger)"
      : t === "warn"
      ? "var(--warning)"
      : t === "success"
      ? "var(--success)"
      : "var(--primary)";

  return (
    <div className="surface-card p-5">
      <PanelHeader icon={Share2} title="Network Graph" subtitle="entity links · mule clusters" />
      <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_140px]">
        <div className="relative overflow-hidden rounded-md border border-border/60 bg-card/40">
          <div className="absolute inset-0 grid-bg opacity-30" />
          <svg viewBox="0 0 100 100" className="relative h-56 w-full">
            {nodes.slice(1).map((n, i) => (
              <motion.line
                key={n.id}
                x1={50}
                y1={50}
                x2={n.x}
                y2={n.y}
                stroke={color(n.tone)}
                strokeOpacity={0.35}
                strokeWidth={0.4}
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ delay: i * 0.05, duration: 0.6 }}
              />
            ))}
            {nodes.map((n, i) => (
              <motion.g
                key={n.id}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.15 + i * 0.04 }}
              >
                <circle
                  cx={n.x}
                  cy={n.y}
                  r={n.r + 2}
                  fill={color(n.tone)}
                  fillOpacity={0.15}
                />
                <circle cx={n.x} cy={n.y} r={n.r} fill={color(n.tone)} />
                {n.id === "C" && (
                  <motion.circle
                    cx={n.x}
                    cy={n.y}
                    r={n.r}
                    fill="none"
                    stroke={color(n.tone)}
                    strokeOpacity={0.6}
                    animate={{ r: [n.r, n.r + 12], opacity: [0.6, 0] }}
                    transition={{ duration: 2.2, repeat: Infinity }}
                  />
                )}
              </motion.g>
            ))}
          </svg>
        </div>
        <div className="space-y-2">
          {[
            { l: "Clusters", v: "37", c: "var(--primary)" },
            { l: "Mule risk", v: "4 hi", c: "var(--danger)" },
            { l: "New links", v: "+128", c: "var(--success)" },
            { l: "Density", v: "0.42", c: "var(--info)" },
          ].map((s) => (
            <div key={s.l} className="rounded-md border border-border/60 bg-card/40 px-3 py-2">
              <p className="font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
                {s.l}
              </p>
              <p
                className="font-display text-base font-semibold tabular-nums"
                style={{ color: s.c }}
              >
                {s.v}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---------------- Transaction Scorer ---------------- */
function TransactionScorer() {
  const score = 78;
  const circ = 2 * Math.PI * 42;
  const txns = [
    { id: "TX-8842311", a: "$4,820.00", s: 94, t: "danger" },
    { id: "TX-8842298", a: "$129.40", s: 41, t: "warn" },
    { id: "TX-8842277", a: "$2,210.00", s: 86, t: "danger" },
    { id: "TX-8842245", a: "$910.00", s: 72, t: "warn" },
    { id: "TX-8842231", a: "$320.00", s: 28, t: "success" },
  ];

  return (
    <div className="surface-card p-5">
      <PanelHeader icon={Receipt} title="Transaction Scorer" subtitle="fused risk · per-event" />
      <div className="mt-4 grid gap-4 sm:grid-cols-[160px_1fr] items-center">
        <div className="relative mx-auto h-36 w-36">
          <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
            <circle cx="50" cy="50" r="42" stroke="oklch(0.3 0.025 252)" strokeWidth="6" fill="none" />
            <motion.circle
              cx="50"
              cy="50"
              r="42"
              stroke="url(#scorer-grad)"
              strokeWidth="6"
              strokeLinecap="round"
              fill="none"
              strokeDasharray={circ}
              initial={{ strokeDashoffset: circ }}
              animate={{ strokeDashoffset: circ - (circ * score) / 100 }}
              transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
            />
            <defs>
              <linearGradient id="scorer-grad" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stopColor="oklch(0.82 0.16 195)" />
                <stop offset="100%" stopColor="oklch(0.7 0.2 25)" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-display text-3xl font-semibold tabular-nums">{score}</span>
            <span className="font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
              fused risk
            </span>
          </div>
        </div>
        <div className="space-y-1.5">
          {txns.map((t, i) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: 6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="grid grid-cols-[110px_1fr_50px] items-center gap-2 font-mono-tech text-[11px]"
            >
              <span className="text-muted-foreground">{t.id}</span>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${t.s}%` }}
                  transition={{ delay: 0.2 + i * 0.05, duration: 0.7 }}
                  className="h-full"
                  style={{
                    background:
                      t.t === "danger"
                        ? "var(--danger)"
                        : t.t === "warn"
                        ? "var(--warning)"
                        : "var(--success)",
                  }}
                />
              </div>
              <span className="text-right tabular-nums text-foreground/90">{t.a}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---------------- Risk Distribution ---------------- */
function RiskDistribution() {
  const buckets = [
    { l: "Trusted", v: 64, c: "var(--success)" },
    { l: "Low", v: 18, c: "var(--info)" },
    { l: "Medium", v: 11, c: "var(--warning)" },
    { l: "High", v: 5, c: "var(--danger)" },
    { l: "Critical", v: 2, c: "var(--danger)" },
  ];
  // donut math
  let acc = 0;
  const total = buckets.reduce((s, b) => s + b.v, 0);
  const segs = buckets.map((b) => {
    const start = (acc / total) * 100;
    acc += b.v;
    const end = (acc / total) * 100;
    return { ...b, start, end };
  });

  return (
    <div className="surface-card p-5">
      <PanelHeader icon={PieIcon} title="Risk Distribution" subtitle="last 24h · all agents" />
      <div className="mt-4 grid gap-4 sm:grid-cols-[140px_1fr] items-center">
        <div className="relative mx-auto h-32 w-32">
          <svg viewBox="0 0 36 36" className="-rotate-90">
            {segs.map((s, i) => {
              const c = 2 * Math.PI * 15.9;
              const dash = ((s.end - s.start) / 100) * c;
              const offset = -((s.start / 100) * c);
              return (
                <motion.circle
                  key={s.l}
                  cx="18"
                  cy="18"
                  r="15.9"
                  fill="none"
                  stroke={s.c}
                  strokeWidth="4"
                  initial={{ strokeDasharray: `0 ${c}` }}
                  animate={{ strokeDasharray: `${dash} ${c - dash}`, strokeDashoffset: offset }}
                  transition={{ delay: 0.15 + i * 0.08, duration: 0.7 }}
                />
              );
            })}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-display text-lg font-semibold tabular-nums">2.4M</span>
            <span className="font-mono-tech text-[9px] uppercase tracking-wider text-muted-foreground">
              events
            </span>
          </div>
        </div>
        <div className="space-y-2">
          {buckets.map((b, i) => (
            <motion.div
              key={b.l}
              initial={{ opacity: 0, x: 6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="grid grid-cols-[80px_1fr_42px] items-center gap-2"
            >
              <div className="flex items-center gap-1.5 font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
                <span className="h-2 w-2 rounded-full" style={{ background: b.c }} />
                {b.l}
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${b.v}%` }}
                  transition={{ delay: 0.2 + i * 0.05, duration: 0.7 }}
                  className="h-full"
                  style={{ background: b.c }}
                />
              </div>
              <span className="text-right font-mono-tech text-[10px] tabular-nums text-foreground/90">
                {b.v}%
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---------------- Composer ---------------- */
export function AgentExtras({ id }: { id: AgentId }) {
  if (id === "device") {
    return (
      <div className="grid gap-5">
        <DeviceIntel />
      </div>
    );
  }
  if (id === "behavior") {
    return (
      <div className="grid gap-5 lg:grid-cols-2">
        <BehaviorAnalysis />
        <BehavioralBio />
      </div>
    );
  }
  // orchestrator
  return (
    <div className="grid gap-5">
      <NetworkGraph />
      <div className="grid gap-5 lg:grid-cols-2">
        <TransactionScorer />
        <RiskDistribution />
      </div>
    </div>
  );
}
