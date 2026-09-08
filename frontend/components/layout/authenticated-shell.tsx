import Link from "next/link";
import type { ReactNode } from "react";
import { Logo } from "@/components/brand/logo";
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
        <Link
          className="inline-flex items-center rounded-sm focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
          href="/"
          aria-label="RoundReady home"
        >
          <Logo priority />
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
