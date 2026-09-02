import type { ReactNode } from "react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { RoleShell } from "@/components/layout/role-shell";

export default function CandidateLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={["candidate"]}>
      <RoleShell role="Candidate">{children}</RoleShell>
    </ProtectedRoute>
  );
}
