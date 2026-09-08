"use client";

import Link from "next/link";
import { BriefcaseBusiness, CheckCircle2, Layers3, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { VerificationStatusCard } from "@/components/interviewer/verification-status";
import { useAuth } from "@/components/providers/auth-provider";
import * as api from "@/lib/api/interviewer";
import { isInterviewerProfileComplete } from "@/lib/interviewer-profile";
import type { InterviewerProfile } from "@/types/interviewer";

export function InterviewerDashboard() {
  const { request } = useAuth();
  const [profile, setProfile] = useState<InterviewerProfile | null>(null);
  const [completion, setCompletion] = useState(0);
  useEffect(() => {
    void Promise.all([
      api.getInterviewerProfile(request),
      api.getSkills(request),
      api.getWeeklyRules(request),
    ])
      .then(([loaded, skills, rules]) => {
        setProfile(loaded);
        const fields = [
          isInterviewerProfileComplete(loaded),
          skills.length > 0,
          rules.length > 0,
        ];
        setCompletion(
          Math.round((fields.filter(Boolean).length / fields.length) * 100),
        );
      })
      .catch(() => setProfile(null));
  }, [request]);
  const name = profile?.full_name?.trim().split(/\s+/)[0] ?? null;
  const cards = [
    [
      "Profile completion",
      `${completion}%`,
      CheckCircle2,
      "/interviewer/profile",
    ],
    [
      "Skills & domains",
      profile ? "Manage" : "—",
      Layers3,
      "/interviewer/skills",
    ],
    [
      "Completed interviews",
      profile ? String(profile.completed_interviews) : "—",
      BriefcaseBusiness,
      "/interviewer/sessions",
    ],
    [
      "Average rating",
      profile && profile.rating_count > 0 ? profile.rating_average : "—",
      Star,
      "/interviewer/sessions",
    ],
  ] as const;
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Welcome back{name ? `, ${name}` : ""}!
        </h1>
        <p className="mt-1 text-slate-600">
          Manage your profile, availability and interviews.
        </p>
      </header>
      {profile ? (
        <VerificationStatusCard
          status={profile.verification_status}
          reason={profile.verification_reason}
        />
      ) : (
        <div className="rounded-xl border border-dashed bg-white p-5">
          <p className="font-medium">
            Complete your professional profile to begin verification.
          </p>
          <Link
            href="/interviewer/profile"
            className="mt-3 inline-block text-sm font-semibold text-blue-700"
          >
            Create profile
          </Link>
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(([label, value, Icon, href]) => (
          <Link
            key={label}
            href={href}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300"
          >
            <Icon className="h-6 w-6 text-blue-600" aria-hidden="true" />
            <p className="mt-4 text-sm text-slate-600">{label}</p>
            <p className="mt-1 text-2xl font-bold text-slate-950">{value}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
