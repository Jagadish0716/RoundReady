import type { ReactNode } from "react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { RoleShell } from "@/components/layout/role-shell";

export default function InterviewerLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <ProtectedRoute allowedRoles={["interviewer"]}>
      <RoleShell role="Interviewer">{children}</RoleShell>
    </ProtectedRoute>
  );
}
