"use client";

import type { ReactNode } from "react";
import { CandidateSidebar } from "@/components/candidate/candidate-profile-chrome";
import { useAuth } from "@/components/providers/auth-provider";

export function CandidateShell({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  const displayName =
    state.status === "authenticated"
      ? state.session.user.email.split("@")[0]
      : "Candidate";

  return (
    <div className="grid min-w-0 gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
      <CandidateSidebar displayName={displayName} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
