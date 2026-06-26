import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useDashboardData } from "@/hooks/use-fraud-data";

export function RiskChart() {
  const { timeseries } = useDashboardData();
  const data = timeseries.length > 0 ? timeseries : getFallbackData();

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 12, left: -16, bottom: 0 }}>
          <defs>
            <linearGradient id="g-orch" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="oklch(0.82 0.16 195)" stopOpacity={0.55} />
              <stop offset="100%" stopColor="oklch(0.82 0.16 195)" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="g-beh" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="oklch(0.78 0.17 158)" stopOpacity={0.45} />
              <stop offset="100%" stopColor="oklch(0.78 0.17 158)" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="g-dev" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="oklch(0.74 0.14 240)" stopOpacity={0.4} />
              <stop offset="100%" stopColor="oklch(0.74 0.14 240)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="oklch(0.3 0.025 252 / 0.4)" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="t" tick={{ fill: "oklch(0.66 0.025 245)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={false} interval={5} />
          <YAxis tick={{ fill: "oklch(0.66 0.025 245)", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={false} width={36} />
          <Tooltip contentStyle={{ background: "oklch(0.215 0.022 252)", border: "1px solid oklch(0.3 0.025 252)", borderRadius: 8, fontSize: 12, fontFamily: "JetBrains Mono" }} labelStyle={{ color: "oklch(0.88 0.01 220)" }} />
          <Area type="monotone" dataKey="device" stroke="oklch(0.74 0.14 240)" strokeWidth={1.5} fill="url(#g-dev)" />
          <Area type="monotone" dataKey="behavior" stroke="oklch(0.78 0.17 158)" strokeWidth={1.5} fill="url(#g-beh)" />
          <Area type="monotone" dataKey="orchestrator" stroke="oklch(0.82 0.16 195)" strokeWidth={2} fill="url(#g-orch)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function getFallbackData() {
  return Array.from({ length: 48 }, (_, i) => {
    const h = String(Math.floor(i / 2)).padStart(2, "0");
    const m = i % 2 ? "30" : "00";
    const t = Math.sin(i * 0.15) * 10 + 25;
    return { t: `${h}:${m}`, behavior: Math.round(t + 5), device: Math.round(t * 0.85), orchestrator: Math.round(t * 1.1 + 3) };
  });
}
