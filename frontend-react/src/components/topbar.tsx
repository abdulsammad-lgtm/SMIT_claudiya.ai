import { SidebarTrigger } from "@/components/ui/sidebar";
import { Bell, Command, LogIn, LogOut, Search, ShieldCheck, X } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { useAuth } from "@/hooks/use-auth";
import { useRef, useState, useEffect, type KeyboardEvent } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function TopBar({ title, subtitle, onSearchChange }: { title: string; subtitle?: string; onSearchChange?: (q: string) => void }) {
  const { user, role, signOut, loading } = useAuth();
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handler as any);
    return () => document.removeEventListener("keydown", handler as any);
  }, []);

  function handleChange(val: string) {
    setQuery(val);
    onSearchChange?.(val);
  }

  const initials = (user?.user_metadata?.full_name as string | undefined)
    ?.split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase()
    ?? user?.email?.slice(0, 2).toUpperCase()
    ?? "··";

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border/70 bg-background/70 px-4 backdrop-blur-xl">
      <SidebarTrigger className="-ml-1" />
      <div className="hidden sm:flex flex-col leading-tight">
        <span className="font-display text-sm font-semibold">{title}</span>
        {subtitle && (
          <span className="font-mono-tech text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            {subtitle}
          </span>
        )}
      </div>

      <div className="ml-auto flex items-center gap-2">
        <div className="hidden md:flex items-center gap-2 surface-card px-3 py-1.5 text-xs text-muted-foreground w-72 focus-within:ring-1 focus-within:ring-ring transition">
          <Search className="h-3.5 w-3.5 shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => handleChange(e.target.value)}
            placeholder="Search accounts, events, policies…"
            className="flex-1 bg-transparent outline-none placeholder:text-muted-foreground/60 text-foreground"
          />
          {query ? (
            <button onClick={() => handleChange("")} className="shrink-0 hover:text-foreground transition">
              <X className="h-3.5 w-3.5" />
            </button>
          ) : (
            <span className="shrink-0 flex items-center gap-1 font-mono-tech text-[10px] text-muted-foreground/50">
              <Command className="h-3 w-3" />K
            </span>
          )}
        </div>
        <button className="relative grid h-9 w-9 place-items-center rounded-md border border-border/80 bg-card hover:bg-accent transition">
          <Bell className="h-4 w-4" />
          <span className="absolute -top-1 -right-1 grid h-4 w-4 place-items-center rounded-full bg-[color:var(--danger)] text-[9px] font-bold text-white">
            7
          </span>
        </button>

        {loading ? (
          <div className="h-9 w-9 rounded-full bg-muted animate-pulse" />
        ) : user ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2 rounded-full bg-[var(--gradient-primary)] pl-0.5 pr-3 py-0.5 text-[11px] font-bold text-primary-foreground hover:opacity-90">
                <span className="grid h-8 w-8 place-items-center rounded-full bg-black/40 text-white">
                  {initials}
                </span>
                <span className="font-mono-tech uppercase tracking-wider">{role ?? "no role"}</span>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <p className="text-xs font-medium truncate">{user.email}</p>
                <p className="font-mono-tech text-[10px] uppercase tracking-wider text-muted-foreground">
                  role · {role ?? "none"}
                </p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to="/admin" className="cursor-pointer">
                  <ShieldCheck className="mr-2 h-4 w-4" /> Admin panel
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => signOut()} className="cursor-pointer text-[color:var(--danger)]">
                <LogOut className="mr-2 h-4 w-4" /> Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Link
            to="/auth"
            className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90"
          >
            <LogIn className="h-3.5 w-3.5" /> Sign in
          </Link>
        )}
      </div>
    </header>
  );
}
