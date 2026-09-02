"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { ForbiddenState } from "@/components/states/forbidden-state";
import { LoadingState } from "@/components/states/loading-state";
import { UnauthorizedState } from "@/components/states/unauthorized-state";
import { useAuth } from "@/components/providers/auth-provider";
import { protectedRouteDecision } from "@/lib/auth/guard";
import type { Role } from "@/types/auth";

export function ProtectedRoute({
  children,
  allowedRoles,
}: {
  children: ReactNode;
  allowedRoles?: readonly Role[];
}) {
  const { state } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const decision = protectedRouteDecision(state, allowedRoles);

  useEffect(() => {
    if (decision === "unauthorized") {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [decision, pathname, router]);

  if (decision === "loading") return <LoadingState />;
  if (decision === "unauthorized") return <UnauthorizedState />;
  if (decision === "forbidden") return <ForbiddenState />;
  return children;
}
