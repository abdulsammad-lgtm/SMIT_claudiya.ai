import { createFileRoute } from "@tanstack/react-router";
import { TopBar } from "@/components/topbar";
import { AgentPage } from "@/components/fraud/agent-page";

export const Route = createFileRoute("/agents/device")({
  head: () => ({
    meta: [
      { title: "Device Agent — Claudiya.ai" },
      { name: "description", content: "Resolves device fingerprints and network reputation into a trust score." },
    ],
  }),
  component: () => (
    <>
      <TopBar title="Device Agent" subtitle="fingerprint · trust" />
      <main className="flex-1 p-4 lg:p-6"><AgentPage id="device" /></main>
    </>
  ),
});
