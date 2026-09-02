import type { AuthState } from "@/lib/auth/state";
import type { Role } from "@/types/auth";

export type RouteDecision = "allow" | "loading" | "unauthorized" | "forbidden";

export function protectedRouteDecision(
  state: AuthState,
  allowedRoles?: readonly Role[],
): RouteDecision {
  if (state.status === "authenticating") return "loading";
  if (state.status === "anonymous") return "unauthorized";
  if (allowedRoles && !allowedRoles.includes(state.session.user.role))
    return "forbidden";
  return "allow";
}
