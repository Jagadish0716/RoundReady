import type { Role } from "@/types/auth";

const roleHomes: Record<Role, string> = {
  candidate: "/candidate",
  interviewer: "/interviewer",
  admin: "/admin",
};

export function roleHome(role: Role): string {
  return roleHomes[role];
}

export function redirectForRole(role: Role, requested: string | null): string {
  const home = roleHome(role);
  if (!requested || !requested.startsWith("/") || requested.startsWith("//"))
    return home;
  return requested === home || requested.startsWith(`${home}/`)
    ? requested
    : home;
}
