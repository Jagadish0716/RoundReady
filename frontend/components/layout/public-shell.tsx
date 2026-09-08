import Link from "next/link";
import type { ReactNode } from "react";
import { Logo } from "@/components/brand/logo";

export function PublicShell({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto min-h-screen max-w-5xl px-6 py-8">
      <header className="mb-12 flex items-center justify-between">
        <Link
          className="inline-flex items-center rounded-sm focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
          href="/"
          aria-label="RoundReady home"
        >
          <Logo priority />
        </Link>
        <nav className="flex gap-4 text-sm" aria-label="Public navigation">
          <Link href="/#interviewers">Browse interviewers</Link>
          <Link href="/login">Login</Link>
          <Link href="/register">Register</Link>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
