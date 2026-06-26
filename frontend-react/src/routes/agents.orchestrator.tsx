import { createFileRoute } from "@tanstack/react-router";
import { TopBar } from "@/components/topbar";
import { AgentPage } from "@/components/fraud/agent-page";

export const Route = createFileRoute("/agents/orchestrator")({
  head: () => ({
    meta: [
      { title: "Orchestrator Agent — Claudiya.ai" },
      { name: "description", content: "The orchestrator fuses agent scores and routes transactions through policy graphs." },
    ],
  }),
  component: () => (
    <>
      <TopBar title="Orchestrator Agent" subtitle="decision fusion" />
      <main className="flex-1 p-4 lg:p-6"><AgentPage id="orchestrator" /></main>
    </>
  ),
});
