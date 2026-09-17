"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Logo } from "@/components/brand/logo";

export function PublicShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  if (pathname === "/login") {
    return <main>{children}</main>;
  }

  return (
    <div className="min-h-screen overflow-x-clip bg-[#f8faff] text-slate-950">
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/95 backdrop-blur-md">
        <div className="mx-auto flex h-18 max-w-7xl items-center justify-between gap-3 px-4 sm:gap-6 sm:px-6 lg:px-8">
          <Link
            className="inline-flex items-center rounded-sm focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
            href="/"
            aria-label="RoundReady home"
          >
            <Logo priority className="sm:w-[190px]" />
          </Link>
          <nav
            className="flex items-center gap-3 text-sm font-medium text-slate-700 sm:gap-5"
            aria-label="Public navigation"
          >
            <Link
              className="hidden hover:text-blue-700 md:inline"
              href="/#interviewers"
            >
              Browse interviewers
            </Link>
            <Link
              className="hidden hover:text-blue-700 lg:inline"
              href="/#how-it-works"
            >
              How it works
            </Link>
            <Link
              className="hidden hover:text-blue-700 lg:inline"
              href="/#why-roundready"
            >
              Why RoundReady
            </Link>
            <Link className="hover:text-blue-700" href="/login">
              Login
            </Link>
            <Link
              className="rounded-lg bg-blue-600 px-3 py-2.5 font-semibold whitespace-nowrap text-white shadow-sm hover:bg-blue-700 hover:no-underline sm:px-4"
              href="/register"
            >
              Get started
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        {children}
      </main>
    </div>
  );
}
