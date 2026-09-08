"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
  Bell,
  CalendarClock,
  CalendarX2,
  CircleCheckBig,
  LayoutDashboard,
  Layers3,
  UserRound,
  Video,
} from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { getInterviewerProfile } from "@/lib/api/interviewer";

const items = [
  ["Dashboard", "/interviewer", LayoutDashboard],
  ["My Profile", "/interviewer/profile", UserRound],
  ["Verification", "/interviewer/verification", CircleCheckBig],
  ["Skills & Domains", "/interviewer/skills", Layers3],
  ["Availability", "/interviewer/availability", CalendarClock],
  ["Blockouts", "/interviewer/blockouts", CalendarX2],
  ["Interview Sessions", "/interviewer/sessions", Video],
  ["Notifications", "/interviewer/notifications", Bell],
] as const;

export function InterviewerShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { request } = useAuth();
  const [name, setName] = useState("Name not provided");
  useEffect(() => {
    let active = true;
    getInterviewerProfile(request)
      .then((profile) => {
        if (active && profile.full_name) setName(profile.full_name);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [request]);
  useEffect(() => {
    function updateName(event: Event) {
      const fullName = (event as CustomEvent<{ fullName?: string | null }>)
        .detail?.fullName;
      setName(fullName?.trim() || "Name not provided");
    }
    window.addEventListener(
      "roundready:interviewer-profile-updated",
      updateName,
    );
    return () =>
      window.removeEventListener(
        "roundready:interviewer-profile-updated",
        updateName,
      );
  }, []);
  return (
    <div className="grid min-w-0 gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
      <aside
        className="rounded-xl border border-slate-200 bg-white p-4 lg:sticky lg:top-6 lg:self-start"
        aria-label="Interviewer navigation"
      >
        <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-blue-100 font-semibold text-blue-700">
            {name.slice(0, 2).toUpperCase()}
          </span>
          <div className="min-w-0">
            <p className="truncate font-semibold text-slate-950">{name}</p>
            <p className="text-sm text-slate-500">Interviewer</p>
          </div>
        </div>
        <nav className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-1">
          {items.map(([label, href, Icon]) => {
            const active =
              href === "/interviewer"
                ? pathname === href
                : pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none ${active ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"}`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="min-w-0">{children}</div>
    </div>
  );
}
