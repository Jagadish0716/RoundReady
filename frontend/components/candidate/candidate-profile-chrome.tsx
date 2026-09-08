import Link from "next/link";
import {
  Bell,
  CalendarDays,
  Check,
  Circle,
  CircleHelp,
  LayoutDashboard,
  Search,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import type { ReactNode } from "react";

export function CandidateSidebar({ displayName }: { displayName: string }) {
  const items = [
    { label: "Dashboard", href: "/candidate", icon: LayoutDashboard },
    {
      label: "My Profile",
      href: "#candidate-profile",
      icon: UserRound,
      active: true,
    },
    { label: "Browse Interviewers", href: "/#interviewers", icon: Search },
    { label: "My Bookings", href: "#interview-sessions", icon: CalendarDays },
    { label: "Notifications", href: "#notifications", icon: Bell },
  ];
  return (
    <aside
      className="rounded-xl border border-slate-200 bg-white p-4 lg:sticky lg:top-6 lg:self-start"
      aria-label="Candidate navigation"
    >
      <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-blue-100 text-blue-600">
          <UserRound aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="truncate font-semibold text-slate-950">{displayName}</p>
          <p className="text-sm text-slate-500">Candidate</p>
        </div>
      </div>
      <nav className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-1">
        {items.map(({ label, href, icon: Icon, active }) => (
          <Link
            key={label}
            href={href}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none ${active ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"}`}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {label}
          </Link>
        ))}
      </nav>
      <div className="mt-6 hidden rounded-lg border border-blue-100 bg-blue-50/60 p-4 lg:block">
        <div className="flex gap-3">
          <CircleHelp className="h-5 w-5 text-blue-600" aria-hidden="true" />
          <div>
            <p className="text-sm font-semibold text-slate-900">Need help?</p>
            <p className="mt-1 text-xs text-slate-600">
              We&apos;re here for you.
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}

export function ProfileHeader({ completion }: { completion: number }) {
  return (
    <header className="flex flex-col gap-5 border-b border-slate-100 pb-6 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Candidate profile
        </h1>
        <p className="mt-1 text-sm text-slate-600 sm:text-base">
          Tell us about yourself to help interviewers understand you better.
        </p>
      </div>
      <div
        className="w-full rounded-lg border border-slate-200 bg-slate-50 p-3 sm:w-48"
        aria-label={`Profile ${completion}% complete`}
      >
        <div className="flex justify-between text-xs font-medium text-slate-700">
          <span>Complete your profile</span>
          <span>{completion}%</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
          <div
            className="h-full rounded-full bg-emerald-500 transition-[width]"
            style={{ width: `${completion}%` }}
          />
        </div>
      </div>
    </header>
  );
}

function InfoCard({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-xl border border-slate-200 bg-white p-5 ${className}`}
    >
      {children}
    </section>
  );
}

export function CandidateProfileHelp() {
  const benefits = [
    "Present your experience clearly",
    "Help interviewers prepare",
    "Keep your interview details current",
  ];
  const tips = [
    "Keep your profile information up to date",
    "Add a clear and professional resume",
    "Mention your current and target roles",
    "Include your LinkedIn profile",
    "Choose the language you’re comfortable with",
  ];
  return (
    <aside
      className="space-y-5 lg:sticky lg:top-6 lg:self-start"
      aria-label="Profile guidance"
    >
      <InfoCard className="border-blue-100 bg-blue-50/60">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-white text-blue-600 shadow-sm">
          <UserRound className="h-7 w-7" aria-hidden="true" />
        </div>
        <h2 className="mt-4 text-lg font-bold text-slate-950">
          A complete profile helps you
        </h2>
        <ul className="mt-4 space-y-3">
          {benefits.map((item) => (
            <li key={item} className="flex gap-2 text-sm text-slate-700">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white">
                <Check className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              {item}
            </li>
          ))}
        </ul>
      </InfoCard>
      <InfoCard className="border-emerald-100 bg-emerald-50/60">
        <div className="flex gap-3">
          <ShieldCheck
            className="h-7 w-7 shrink-0 text-emerald-700"
            aria-hidden="true"
          />
          <div>
            <h2 className="font-bold text-slate-950">
              Your information is protected
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Your profile and resume are accessed through authenticated
              RoundReady services. Resume files are not published as public
              URLs.
            </p>
          </div>
        </div>
      </InfoCard>
      <InfoCard>
        <h2 className="text-lg font-bold text-slate-950">Profile tips</h2>
        <ul className="mt-4 space-y-3">
          {tips.map((tip) => (
            <li key={tip} className="flex gap-2 text-sm text-slate-600">
              <Circle
                className="mt-0.5 h-4 w-4 shrink-0 text-slate-400"
                aria-hidden="true"
              />
              {tip}
            </li>
          ))}
        </ul>
      </InfoCard>
    </aside>
  );
}
