import { Link, useRouterState } from "@tanstack/react-router";
import { Activity, ShieldCheck, GitBranch, Fingerprint, Brain, Settings2, Radar, LogIn } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  useSidebar,
} from "@/components/ui/sidebar";
import { useAuth } from "@/hooks/use-auth";

const NAV = [
  { title: "Dashboard", url: "/", icon: Activity, group: "Operations" },
  { title: "Agent Progress", url: "/progress", icon: Radar, group: "Operations" },
  { title: "Orchestrator", url: "/agents/orchestrator", icon: GitBranch, group: "Agents" },
  { title: "Behavior", url: "/agents/behavior", icon: Brain, group: "Agents" },
  { title: "Device", url: "/agents/device", icon: Fingerprint, group: "Agents" },
  { title: "Admin Panel", url: "/admin", icon: Settings2, group: "Governance", requiresAuth: true },
] as const;

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const pathname = useRouterState({ select: (r) => r.location.pathname });
  const { user, role } = useAuth();

  const groups = Array.from(new Set(NAV.map((n) => n.group)));

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <Link to="/" className="flex items-center gap-2.5 px-2 py-2.5">
          <div className="relative flex h-8 w-8 items-center justify-center rounded-md bg-[var(--gradient-primary)] glow-primary">
            <ShieldCheck className="h-4.5 w-4.5 text-primary-foreground" strokeWidth={2.5} />
          </div>
          {!collapsed && (
            <div className="flex flex-col leading-tight">
              <span className="font-display text-sm font-semibold tracking-tight">CLAUDIYA.AI</span>
              <span className="font-mono-tech text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                fraud · multi-agent
              </span>
            </div>
          )}
        </Link>
      </SidebarHeader>

      <SidebarContent>
        {groups.map((g) => (
          <SidebarGroup key={g}>
            <SidebarGroupLabel className="font-mono-tech text-[10px] uppercase tracking-[0.18em]">
              {g}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {NAV.filter((n) => n.group === g).map((item) => {
                  const active = pathname === item.url;
                  return (
                    <SidebarMenuItem key={item.url}>
                      <SidebarMenuButton asChild isActive={active}>
                        <Link to={item.url} className="flex items-center gap-2">
                          <item.icon className="h-4 w-4" />
                          {!collapsed && (
                            <>
                              <span>{item.title}</span>
                              {"requiresAuth" in item && item.requiresAuth && !user && (
                                <LogIn className="ml-auto h-3 w-3 text-muted-foreground" />
                              )}
                            </>
                          )}
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        {!collapsed && (
          <div className="surface-card px-3 py-2.5 text-[11px]">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inset-0 rounded-full bg-[color:var(--success)] opacity-60 pulse-dot" />
                <span className="relative h-2 w-2 rounded-full bg-[color:var(--success)]" />
              </span>
              <span className="font-mono-tech uppercase tracking-wider text-muted-foreground">
                system nominal
              </span>
            </div>
            {user ? (
              <p className="mt-1 font-mono-tech text-[10px] text-muted-foreground truncate">
                {role ?? "no role"} · {user.email}
              </p>
            ) : (
              <p className="mt-1 font-mono-tech text-[10px] text-muted-foreground">
                v4.21.0 · public preview
              </p>
            )}
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
