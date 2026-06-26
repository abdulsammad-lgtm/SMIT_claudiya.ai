import { createFileRoute, Outlet } from "@tanstack/react-router";

// Protected layout — currently allows all access (auth is handled by FastAPI backend)
export const Route = createFileRoute("/_authenticated")({
  ssr: false,
  component: () => <Outlet />,
});
