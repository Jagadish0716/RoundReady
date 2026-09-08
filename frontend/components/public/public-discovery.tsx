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

export function PublicDiscovery({
  authenticated = false,
}: {
  authenticated?: boolean;
}) {
  const [interviewers, setInterviewers] = useState<PublicInterviewer[]>([]);
  const [slots, setSlots] = useState<PublicSlot[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const starts = new Date();
    const ends = new Date(starts);
    ends.setDate(ends.getDate() + 30);
    void Promise.all([
      listPublicInterviewers(),
      listPublicSlots(starts.toISOString(), ends.toISOString()),
    ])
      .then(([people, available]) => {
        setInterviewers(people);
        setSlots(available);
      })
      .catch(() =>
        setError("Public interview availability could not be loaded."),
      )
      .finally(() => setLoading(false));
  }, []);
  return (
    <section
      id="interviewers"
      className="space-y-8"
      aria-labelledby="discovery-heading"
    >
      <header>
        <p className="text-sm font-semibold text-blue-700">
          {authenticated
            ? "Choose a verified interviewer and an available slot."
            : "Explore freely. Sign in when you’re ready to book."}
        </p>
        <h2 id="discovery-heading" className="mt-2 text-3xl font-semibold">
          Verified interviewers
        </h2>
        <p className="mt-2 text-neutral-600">
          Browse skills, trust checks, and available ₹200 interview slots
          without an account.
        </p>
      </header>
      {error && (
        <p role="alert" className="rounded-md bg-red-50 p-3 text-red-800">
          {error}
        </p>
      )}
      {loading ? <p role="status">Loading verified interviewers…</p> : null}
      {!loading && interviewers.length === 0 && !error ? (
        <p role="status" className="rounded-md bg-slate-50 p-4 text-slate-600">
          No interview slots are available right now. Please check again soon.
        </p>
      ) : null}
      <div className="grid gap-6 md:grid-cols-2">
        {interviewers.map((person) => {
          const available = slots.filter(
            (slot) => slot.interviewer_id === person.interviewer_id,
          );
          return (
            <article
              key={person.interviewer_id}
              className="rounded-xl border bg-white p-5 shadow-sm"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold tracking-wide text-green-700 uppercase">
                    RoundReady Verified
                  </p>
                  <h3 className="mt-1 text-xl font-semibold">
                    {person.headline}
                  </h3>
                  <p className="text-sm text-neutral-600">
                    {person.job_title ?? "Technology interviewer"} ·{" "}
                    {person.experience_years} years
                  </p>
                </div>
                <strong>{money(person.price_paise)}</strong>
              </div>
              {person.bio && (
                <p className="mt-3 text-sm text-neutral-700">{person.bio}</p>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                {person.skills.map((skill) => (
                  <span
                    key={skill.id}
                    className="rounded-full bg-neutral-100 px-3 py-1 text-xs"
                  >
                    {skill.domain} · {skill.skill_name}
                  </span>
                ))}
              </div>
              <ul className="mt-4 space-y-1 text-sm text-neutral-700">
                <li>
                  Interview language: {person.interview_languages.join(", ")}
                </li>
                <li>
                  ✓ Professional experience{" "}
                  {person.professional_experience_reviewed
                    ? "reviewed"
                    : "verification complete"}
                </li>
                <li>
                  ✓ Screening{" "}
                  {person.screening_passed ? "passed" : "verification complete"}
                </li>
              </ul>
              <div className="mt-5 space-y-3">
                <h4 className="font-medium">Available slots</h4>
                {available.length === 0 ? (
                  <p className="text-sm text-neutral-500">
                    No slots available in the next 30 days.
                  </p>
                ) : (
                  available.slice(0, 4).map((slot) => {
                    const next = `/candidate?slot=${encodeURIComponent(slot.id)}&interviewer=${encodeURIComponent(person.interviewer_id)}`;
                    return (
                      <div
                        key={slot.id}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"
                      >
                        <div>
                          <p className="text-sm font-medium">
                            {slot.domain} · {slot.topic}
                          </p>
                          <p className="text-xs text-neutral-600">
                            {new Date(slot.starts_at).toLocaleString()}
                          </p>
                        </div>
                        <Button asChild size="sm">
                          <Link
                            href={
                              authenticated
                                ? next
                                : `/login?next=${encodeURIComponent(next)}`
                            }
                          >
                            Book interview
                          </Link>
                        </Button>
                      </div>
                    );
                  })
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
