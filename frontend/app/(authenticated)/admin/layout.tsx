import type { ReactNode } from "react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { RoleShell } from "@/components/layout/role-shell";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={["admin"]}>
      <RoleShell role="Admin">{children}</RoleShell>
    </ProtectedRoute>
  );
}
