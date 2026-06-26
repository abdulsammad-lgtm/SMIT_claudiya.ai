import { createFileRoute, Link, useNavigate, useSearch } from "@tanstack/react-router";
import { motion } from "motion/react";
import { z } from "zod";
import { ShieldCheck } from "lucide-react";

const searchSchema = z.object({
  redirect: z.string().optional().catch(undefined),
});

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — Claudiya.ai" },
      { name: "description", content: "Authenticate to access the Claudiya.ai fraud-detection console." },
      { name: "robots", content: "noindex" },
    ],
  }),
  validateSearch: searchSchema,
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();
  const handleClick = () => navigate({ to: "/", replace: true });

  return (
    <div className="relative flex min-h-screen w-full items-center justify-center bg-background px-4 py-10">
      <div className="absolute inset-0 grid-bg opacity-30" />
      <div className="absolute -top-32 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-[var(--gradient-primary)] opacity-20 blur-3xl" />

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="surface-card relative w-full max-w-md p-7 text-center"
      >
        <Link to="/" className="flex items-center justify-center gap-2.5">
          <div className="grid h-9 w-9 place-items-center rounded-md bg-[var(--gradient-primary)] glow-primary">
            <ShieldCheck className="h-5 w-5 text-primary-foreground" strokeWidth={2.5} />
          </div>
          <div className="leading-tight text-left">
            <p className="font-display text-sm font-semibold tracking-tight">CLAUDIYA.AI</p>
            <p className="font-mono-tech text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              secure console access
            </p>
          </div>
        </Link>

        <h1 className="mt-8 font-display text-xl font-semibold tracking-tight">
          Auth via FastAPI
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Authentication is handled by the FastAPI backend at port 8000.
          You are already signed in as admin for local development.
        </p>

        <button
          onClick={handleClick}
          className="mt-8 inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition"
        >
          <ShieldCheck className="h-4 w-4" />
          Go to Dashboard
        </button>
      </motion.div>
    </div>
  );
}
