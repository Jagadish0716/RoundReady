import Link from "next/link";
import { Bell } from "lucide-react";
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
  const candidate = title.startsWith("Candidate");
  const interviewer = title.startsWith("Interviewer");
  if (!candidate && !interviewer)
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
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link
            className="inline-flex items-center rounded-sm focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
            href="/"
            aria-label="RoundReady home"
          >
            <Logo priority />
          </Link>
          <nav
            className="hidden items-center gap-7 text-sm font-medium text-slate-700 md:flex"
            aria-label={`${candidate ? "Candidate" : "Interviewer"} shortcuts`}
          >
            {candidate ? (
              <Link href="/candidate/interviews">Browse Interviewers</Link>
            ) : (
              <span>Interviewer workspace</span>
            )}
          </nav>
          <div className="flex items-center gap-4">
            <Link
              href={
                candidate
                  ? "/candidate/notifications"
                  : "/interviewer/notifications"
              }
              aria-label="Notifications"
              className="relative rounded-full p-2 text-slate-600 hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
            >
              <Bell className="h-5 w-5" aria-hidden="true" />
            </Link>
            <LogoutButton />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:py-8">
        {children}
      </main>
    </div>
  );
}
