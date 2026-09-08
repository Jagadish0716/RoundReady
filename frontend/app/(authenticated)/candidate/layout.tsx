import type { ReactNode } from "react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { CandidateShell } from "@/components/candidate/candidate-shell";
import { RoleShell } from "@/components/layout/role-shell";

export default function CandidateLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={["candidate"]}>
      <RoleShell role="Candidate">
        <CandidateShell>{children}</CandidateShell>
      </RoleShell>
    </ProtectedRoute>
  );
}
