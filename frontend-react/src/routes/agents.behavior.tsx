import { createFileRoute } from "@tanstack/react-router";
import { TopBar } from "@/components/topbar";
import { AgentPage } from "@/components/fraud/agent-page";

export const Route = createFileRoute("/agents/behavior")({
  head: () => ({
    meta: [
      { title: "Behavior Agent — Claudiya.ai" },
      { name: "description", content: "Models session telemetry and per-user baselines for anomaly detection." },
    ],
  }),
  component: () => (
    <>
      <TopBar title="Behavior Agent" subtitle="session telemetry" />
      <main className="flex-1 p-4 lg:p-6"><AgentPage id="behavior" /></main>
    </>
  ),
});
