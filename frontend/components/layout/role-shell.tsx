import type { ReactNode } from "react";

import { AuthenticatedShell } from "@/components/layout/authenticated-shell";

export function RoleShell({
  role,
  children,
}: {
  role: string;
  children: ReactNode;
}) {
  return (
    <AuthenticatedShell title={`${role} workspace`}>
      {children}
    </AuthenticatedShell>
  );
}
