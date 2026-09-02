import Link from "next/link";
import type { ReactNode } from "react";
import { LogoutButton } from "@/components/auth/logout-button";

export function AuthenticatedShell({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto min-h-screen max-w-6xl px-6 py-8">
      <header className="mb-10 flex items-center justify-between border-b pb-4">
        <Link className="font-semibold" href="/">
          RoundReady
        </Link>
        <div className="flex items-center gap-4">
          <span className="text-sm text-neutral-600">{title}</span>
          <LogoutButton />
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}
