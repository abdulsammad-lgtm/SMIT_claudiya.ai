// Deterministic-ish mock data for the fraud detection UI.
export type Severity = "low" | "medium" | "high" | "critical";
export type AgentId = "orchestrator" | "behavior" | "device";
export type AgentStatus = "idle" | "scanning" | "analyzing" | "blocked" | "alert";

export interface AgentMeta {
  id: AgentId;
  name: string;
  tagline: string;
  description: string;
  accent: string; // tailwind text color class for accent
  pipeline: { label: string; weight: number }[];
}

export const AGENTS: AgentMeta[] = [
  {
    id: "orchestrator",
    name: "Orchestrator Agent",
    tagline: "Decision fusion · policy routing",
    description:
      "Coordinates downstream agents, fuses risk scores, and routes transactions through the policy graph.",
    accent: "text-primary",
    pipeline: [
      { label: "Ingest event", weight: 12 },
      { label: "Score fusion", weight: 38 },
      { label: "Policy evaluation", weight: 30 },
      { label: "Action dispatch", weight: 20 },
    ],
  },
  {
    id: "behavior",
    name: "Behavior Agent",
    tagline: "Session telemetry · velocity",
    description:
      "Models typing cadence, navigation rhythm, and transaction velocity against a per-user baseline.",
    accent: "text-[color:var(--success)]",
    pipeline: [
      { label: "Session capture", weight: 18 },
      { label: "Baseline diff", weight: 32 },
      { label: "Anomaly cluster", weight: 28 },
      { label: "Risk emit", weight: 22 },
    ],
  },
  {
    id: "device",
    name: "Device Agent",
    tagline: "Fingerprint · network · trust",
    description:
      "Resolves device fingerprints, ASN reputation and emulator signals into a hardware-rooted trust score.",
    accent: "text-[color:var(--info)]",
    pipeline: [
      { label: "Fingerprint", weight: 22 },
      { label: "ASN lookup", weight: 24 },
      { label: "Emulator probe", weight: 26 },
      { label: "Trust verdict", weight: 28 },
    ],
  },
];

export const KPIS = [
  { label: "Events / sec", value: "12,847", delta: "+4.2%", positive: true },
  { label: "Blocked today", value: "1,392", delta: "+18.7%", positive: false },
  { label: "Avg decision", value: "84 ms", delta: "-6 ms", positive: true },
  { label: "Model precision", value: "98.4%", delta: "+0.3%", positive: true },
];

export const RISK_TIMESERIES = Array.from({ length: 48 }, (_, i) => {
  const t = i / 47;
  const base = 22 + Math.sin(t * Math.PI * 2.4) * 14 + Math.cos(t * 9) * 5;
  const spike = i === 31 ? 42 : i === 32 ? 38 : 0;
  return {
    t: `${String(Math.floor(i / 2)).padStart(2, "0")}:${i % 2 ? "30" : "00"}`,
    behavior: Math.max(4, Math.round(base + spike + 6)),
    device: Math.max(4, Math.round(base * 0.85 + spike * 0.7)),
    orchestrator: Math.max(4, Math.round(base * 1.1 + spike * 1.05 + 3)),
  };
});

export interface ThreatEvent {
  id: string;
  ts: string;
  account: string;
  amount: string;
  country: string;
  vector: string;
  severity: Severity;
  agent: AgentId;
  action: "allowed" | "review" | "challenged" | "blocked";
}

export const THREATS: ThreatEvent[] = [
  { id: "TX-8842311", ts: "12:42:09", account: "acc_8821", amount: "$4,820.00", country: "RO", vector: "Card-not-present · velocity", severity: "critical", agent: "behavior", action: "blocked" },
  { id: "TX-8842298", ts: "12:41:51", account: "acc_5512", amount: "$129.40", country: "US", vector: "New device · low trust", severity: "medium", agent: "device", action: "challenged" },
  { id: "TX-8842277", ts: "12:41:30", account: "acc_9930", amount: "$2,210.00", country: "NG", vector: "Emulator fingerprint", severity: "high", agent: "device", action: "blocked" },
  { id: "TX-8842260", ts: "12:41:12", account: "acc_1129", amount: "$58.10", country: "DE", vector: "Off-pattern session", severity: "low", agent: "behavior", action: "review" },
  { id: "TX-8842245", ts: "12:40:58", account: "acc_7740", amount: "$910.00", country: "BR", vector: "ASN repeat offender", severity: "high", agent: "orchestrator", action: "blocked" },
  { id: "TX-8842231", ts: "12:40:41", account: "acc_2210", amount: "$320.00", country: "GB", vector: "Geo jump", severity: "medium", agent: "orchestrator", action: "challenged" },
  { id: "TX-8842210", ts: "12:40:22", account: "acc_4498", amount: "$12.99", country: "CA", vector: "Trusted session", severity: "low", agent: "behavior", action: "allowed" },
];

export const GUARDRAILS: Record<AgentId, { title: string; detail: string; status: "active" | "draft" }[]> = {
  orchestrator: [
    { title: "Two-agent consensus on block", detail: "A block action requires ≥2 agents above their decision threshold.", status: "active" },
    { title: "Hard cap on auto-block velocity", detail: "Auto-block rate cannot exceed 0.8% of traffic in a 5-minute window.", status: "active" },
    { title: "Human review for amounts > $10,000", detail: "All transactions over $10k are routed to manual review queue.", status: "active" },
    { title: "PII redaction in audit logs", detail: "Card PAN, CVV, and full names are tokenised before logging.", status: "active" },
    { title: "Shadow mode for new policies", detail: "Policies <72h old run in shadow and never affect live decisions.", status: "draft" },
  ],
  behavior: [
    { title: "Minimum session length", detail: "Behavior model requires ≥30s of telemetry before emitting a risk score.", status: "active" },
    { title: "Per-user baseline freshness", detail: "Baseline must be ≤30 days old or the model defers to Orchestrator.", status: "active" },
    { title: "No biometric raw retention", detail: "Keystroke and pointer streams discarded after feature extraction.", status: "active" },
    { title: "Bias guard on geography", detail: "Risk delta capped at ±15% across protected geographic cohorts.", status: "active" },
  ],
  device: [
    { title: "Fingerprint entropy floor", detail: "Reject signals below 18 bits of entropy — treat as unknown device.", status: "active" },
    { title: "ASN allowlist override", detail: "Enterprise allowlist bypasses ASN reputation downgrade.", status: "active" },
    { title: "Emulator probe rate limit", detail: "Probe at most 1 / device / hour to avoid measurement bias.", status: "active" },
    { title: "Rooted device challenge", detail: "Rooted / jailbroken devices trigger step-up auth, never silent block.", status: "active" },
  ],
};

export const AUDIT_EVENTS = [
  { ts: "12:42:11", actor: "orchestrator", msg: "Fused score 0.94 → BLOCK TX-8842311" },
  { ts: "12:42:09", actor: "behavior", msg: "Velocity anomaly +4.2σ on acc_8821" },
  { ts: "12:42:07", actor: "device", msg: "Fingerprint match against known mule cluster" },
  { ts: "12:41:58", actor: "orchestrator", msg: "Policy P-114 evaluated · 3 rules matched" },
  { ts: "12:41:42", actor: "device", msg: "Emulator probe positive · acc_9930" },
  { ts: "12:41:30", actor: "orchestrator", msg: "Step-up challenge issued to acc_5512" },
  { ts: "12:41:12", actor: "behavior", msg: "Session 7a13 below confidence floor" },
  { ts: "12:40:58", actor: "orchestrator", msg: "ASN AS-209 flagged · routing to review" },
];

export const ADMIN_USERS = [
  { name: "Maya Okafor", role: "Fraud Lead", email: "maya@claudiya.ai", status: "online", mfa: true },
  { name: "Diego Marín", role: "Risk Analyst", email: "diego@claudiya.ai", status: "online", mfa: true },
  { name: "Aiko Tanaka", role: "Policy Eng", email: "aiko@claudiya.ai", status: "away", mfa: true },
  { name: "Samuel Reiss", role: "ML Eng", email: "sam@claudiya.ai", status: "offline", mfa: false },
  { name: "Priya Iyer", role: "Compliance", email: "priya@claudiya.ai", status: "online", mfa: true },
];

export const POLICIES = [
  { id: "P-101", name: "CNP velocity block", scope: "Orchestrator", trigger: ">5 attempts / 60s", action: "Block", enabled: true },
  { id: "P-114", name: "Emulator → step-up", scope: "Device", trigger: "Emulator probe positive", action: "Step-up", enabled: true },
  { id: "P-122", name: "Geo jump challenge", scope: "Behavior", trigger: ">1,500km in <30m", action: "Challenge", enabled: true },
  { id: "P-130", name: "Mule cluster auto-block", scope: "Orchestrator", trigger: "Fingerprint ∈ cluster", action: "Block", enabled: true },
  { id: "P-141", name: "High-value review", scope: "Orchestrator", trigger: "Amount > $10,000", action: "Review", enabled: true },
  { id: "P-148", name: "Off-hours friction", scope: "Behavior", trigger: "02:00–05:00 local", action: "Challenge", enabled: false },
];
