import Link from "next/link";
import type { ReactNode } from "react";

export function PublicShell({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto min-h-screen max-w-5xl px-6 py-8">
      <header className="mb-12 flex items-center justify-between">
        <Link className="text-xl font-semibold" href="/">
          RoundReady
        </Link>
        <nav className="flex gap-4 text-sm" aria-label="Public navigation">
          <Link href="/login">Login</Link>
          <Link href="/register">Register</Link>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
