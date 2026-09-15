"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  listPublicInterviewers,
  listPublicSlots,
} from "@/lib/api/public-discovery";
import type { PublicInterviewer, PublicSlot } from "@/types/public-discovery";

const money = (paise: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(paise / 100);

function formatSlotTime(slot: PublicSlot) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(slot.starts_at));
}

export function PublicInterviewerProfile({ id }: { id: string }) {
  const [interviewer, setInterviewer] = useState<PublicInterviewer | null>(
    null,
  );
  const [slots, setSlots] = useState<PublicSlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const starts = new Date();
    const ends = new Date(starts);
    ends.setDate(ends.getDate() + 30);
    void Promise.all([
      listPublicInterviewers(),
      listPublicSlots(starts.toISOString(), ends.toISOString()),
    ])
      .then(([people, available]) => {
        setInterviewer(
          people.find((person) => person.interviewer_id === id) ?? null,
        );
        setSlots(
          available
            .filter((slot) => slot.interviewer_id === id)
            .sort(
              (left, right) =>
                new Date(left.starts_at).getTime() -
                new Date(right.starts_at).getTime(),
            ),
        );
      })
      .catch(() =>
        setError("This interviewer profile could not be loaded right now."),
      )
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p role="status">Loading interviewer profile...</p>;

  if (error) {
    return (
      <p role="alert" className="rounded-md bg-red-50 p-3 text-red-800">
        {error}
      </p>
    );
  }

  if (!interviewer) {
    return (
      <div className="space-y-4">
        <p role="status" className="rounded-md bg-slate-50 p-4 text-slate-600">
          This public interviewer profile is not available.
        </p>
        <Button asChild variant="outline">
          <Link href="/#interviewers">Back to interviewers</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <Link className="text-sm font-medium text-blue-700" href="/#interviewers">
        Back to interviewers
      </Link>

      <section className="grid gap-8 md:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="space-y-4">
          <p className="text-xs font-semibold tracking-wide text-green-700 uppercase">
            RoundReady Verified
          </p>
          <h1 className="text-4xl font-semibold tracking-tight">
            {interviewer.full_name ?? "Name not provided"}
          </h1>
          <p className="text-xl font-medium text-slate-700">
            {interviewer.headline}
          </p>
          <p className="text-neutral-600">
            {interviewer.job_title ?? "Technology interviewer"} ·{" "}
            {interviewer.experience_years} years of experience
          </p>
          {interviewer.bio ? (
            <p className="max-w-3xl leading-7 text-neutral-700">
              {interviewer.bio}
            </p>
          ) : null}
        </div>

        <aside className="h-fit rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-neutral-600">Interview price</p>
          <p className="mt-1 text-3xl font-semibold">
            {money(interviewer.price_paise)}
          </p>
          <p className="mt-4 text-sm text-neutral-700">
            Interview language:{" "}
            <span className="font-medium">
              {interviewer.interview_languages.join(", ")}
            </span>
          </p>
        </aside>
      </section>

      <section className="space-y-4" aria-labelledby="skills-heading">
        <h2 id="skills-heading" className="text-2xl font-semibold">
          Skills and domains
        </h2>
        <div className="flex flex-wrap gap-2">
          {interviewer.skills.map((skill) => (
            <span
              key={skill.id}
              className="rounded-full bg-neutral-100 px-3 py-1 text-sm text-neutral-700"
            >
              {skill.domain} · {skill.skill_name}
            </span>
          ))}
        </div>
      </section>

      <section className="space-y-4" aria-labelledby="slots-heading">
        <h2 id="slots-heading" className="text-2xl font-semibold">
          Available slots
        </h2>
        {slots.length === 0 ? (
          <p className="rounded-md bg-slate-50 p-4 text-slate-600">
            No slots are available in the next 30 days.
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {slots.map((slot) => {
              const next = `/candidate?slot=${encodeURIComponent(slot.id)}&interviewer=${encodeURIComponent(interviewer.interviewer_id)}`;
              return (
                <div
                  key={slot.id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-neutral-200 bg-white p-4"
                >
                  <div>
                    <p className="font-medium">
                      {slot.domain} · {slot.topic}
                    </p>
                    <p className="text-sm text-neutral-600">
                      {formatSlotTime(slot)}
                    </p>
                  </div>
                  <Button asChild size="sm">
                    <Link href={`/login?next=${encodeURIComponent(next)}`}>
                      Book interview
                    </Link>
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
