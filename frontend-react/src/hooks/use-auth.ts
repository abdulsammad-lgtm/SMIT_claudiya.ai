export type AppRole = "admin" | "analyst" | "viewer";

const ROLE_RANK: Record<AppRole, number> = { admin: 0, analyst: 1, viewer: 2 };

export function useAuth() {
  return {
    session: { user: { id: "1", email: "abdulsamad9ii11@gmail.com" } },
    user: { id: "1", email: "abdulsamad9ii11@gmail.com", user_metadata: { full_name: "Abdul Samad" } },
    role: "admin" as AppRole,
    loading: false,
    signOut: async () => {},
  };
}

export function hasAtLeast(role: AppRole | null, minimum: AppRole): boolean {
  if (!role) return false;
  return ROLE_RANK[role] <= ROLE_RANK[minimum];
}
