"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BadgeCheck, CalendarClock, Languages, UserRound } from "lucide-react";
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

function formatSlotTime(slot: PublicSlot | undefined) {
  if (!slot) return "No slots in the next 30 days";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(slot.starts_at));
}

function uniqueValues(values: string[]) {
  return [...new Set(values.filter(Boolean))];
}

export function PublicDiscovery({
  authenticated = false,
}: {
  authenticated?: boolean;
}) {
  const [interviewers, setInterviewers] = useState<PublicInterviewer[]>([]);
  const [slots, setSlots] = useState<PublicSlot[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [domainFilter, setDomainFilter] = useState("all");
  const [skillFilter, setSkillFilter] = useState("all");
  const [availabilityFilter, setAvailabilityFilter] = useState("all");
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
  const domains = uniqueValues(
    interviewers.flatMap((person) =>
      person.skills.map((skill) => skill.domain),
    ),
  ).sort();
  const skills = uniqueValues(
    interviewers.flatMap((person) =>
      person.skills.map((skill) => skill.skill_name),
    ),
  ).sort();
  const visibleInterviewers = interviewers.filter((person) => {
    const matchesDomain =
      domainFilter === "all" ||
      person.skills.some((skill) => skill.domain === domainFilter);
    const matchesSkill =
      skillFilter === "all" ||
      person.skills.some((skill) => skill.skill_name === skillFilter);
    const hasAvailability = slots.some(
      (slot) => slot.interviewer_id === person.interviewer_id,
    );
    return (
      matchesDomain &&
      matchesSkill &&
      (availabilityFilter === "all" || hasAvailability)
    );
  });
  return (
    <section
      id="interviewers"
      className="scroll-mt-24 space-y-9 rounded-[2rem] border border-slate-200 bg-white px-5 py-9 shadow-[0_28px_80px_-55px_rgba(15,23,42,0.4)] sm:px-8 sm:py-11 lg:px-10"
      aria-labelledby="discovery-heading"
    >
      <header className="max-w-3xl">
        <p className="text-sm font-bold tracking-wider text-blue-700 uppercase">
          {authenticated
            ? "Choose a verified interviewer and an available slot."
            : "Explore freely. Sign in when you’re ready to book."}
        </p>
        <h2
          id="discovery-heading"
          className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl"
        >
          Find the right interviewer for you
        </h2>
        <p className="mt-3 text-lg text-slate-600">
          Browse verified professionals by domain, skills and availability.
        </p>
      </header>
      {!loading && interviewers.length > 0 ? (
        <div
          className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 sm:grid-cols-3"
          aria-label="Interviewer filters"
        >
          <Filter
            label="Domain"
            value={domainFilter}
            onChange={setDomainFilter}
            options={domains}
            allLabel="All domains"
          />
          <Filter
            label="Skill"
            value={skillFilter}
            onChange={setSkillFilter}
            options={skills}
            allLabel="All skills"
          />
          <label className="space-y-1.5">
            <span className="block text-xs font-bold tracking-wide text-slate-500 uppercase">
              Availability
            </span>
            <select
              className="h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none focus:ring-2 focus:ring-blue-600"
              value={availabilityFilter}
              onChange={(event) => setAvailabilityFilter(event.target.value)}
            >
              <option value="all">Any availability</option>
              <option value="available">Available in 30 days</option>
            </select>
          </label>
        </div>
      ) : null}
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
      {!loading &&
      interviewers.length > 0 &&
      visibleInterviewers.length === 0 ? (
        <p
          role="status"
          className="rounded-2xl bg-blue-50 p-5 text-sm text-blue-900"
        >
          No interviewers match these filters. Try a broader selection.
        </p>
      ) : null}
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {visibleInterviewers.map((person) => {
          const available = slots
            .filter((slot) => slot.interviewer_id === person.interviewer_id)
            .sort(
              (left, right) =>
                new Date(left.starts_at).getTime() -
                new Date(right.starts_at).getTime(),
            );
          const nextSlot = available[0];
          const personDomains = uniqueValues(
            person.skills.map((skill) => skill.domain),
          ).slice(0, 3);
          const visibleSkills = person.skills.slice(0, 5);
          const extraSkills = Math.max(
            person.skills.length - visibleSkills.length,
            0,
          );
          return (
            <article
              key={person.interviewer_id}
              className="group flex h-full min-w-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_16px_45px_-35px_rgba(15,23,42,0.55)] transition duration-200 hover:-translate-y-1 hover:border-blue-200 hover:shadow-[0_24px_55px_-34px_rgba(37,99,235,0.4)]"
            >
              <div className="flex grow flex-col gap-4">
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <p className="inline-flex items-center gap-1.5 text-xs font-bold tracking-wide text-emerald-700 uppercase">
                      <BadgeCheck className="h-4 w-4" aria-hidden /> RoundReady
                      Verified
                    </p>
                    <strong className="shrink-0 text-xl text-slate-950">
                      {money(person.price_paise)}
                    </strong>
                  </div>
                  <div className="mt-3 flex min-w-0 items-center gap-3">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
                      <UserRound className="h-5 w-5" aria-hidden />
                    </span>
                    <div className="min-w-0">
                      <h3 className="line-clamp-2 text-xl font-bold break-words text-slate-950">
                        {person.full_name ?? "Name not provided"}
                      </h3>
                      <p className="line-clamp-2 text-sm font-medium break-words text-slate-600">
                        {person.headline}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-neutral-600">
                    {person.experience_years} years of experience
                  </p>
                </div>

                {personDomains.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {personDomains.map((domain) => (
                      <span
                        key={domain}
                        className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-800"
                      >
                        {domain}
                      </span>
                    ))}
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-2">
                  {visibleSkills.map((skill) => (
                    <span
                      key={skill.id}
                      className="rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-700"
                    >
                      {skill.skill_name}
                    </span>
                  ))}
                  {extraSkills > 0 ? (
                    <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-700">
                      +{extraSkills} more
                    </span>
                  ) : null}
                </div>

                <dl className="mt-auto space-y-3 rounded-xl bg-slate-50 p-4 text-sm text-slate-700">
                  <div className="flex justify-between gap-3">
                    <dt className="inline-flex items-center gap-1.5">
                      <Languages
                        className="h-4 w-4 text-slate-400"
                        aria-hidden
                      />
                      Interview language
                    </dt>
                    <dd className="text-right font-medium">
                      {person.interview_languages.join(", ")}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="inline-flex items-center gap-1.5">
                      <CalendarClock
                        className="h-4 w-4 text-slate-400"
                        aria-hidden
                      />
                      Next availability
                    </dt>
                    <dd className="text-right font-medium">
                      {formatSlotTime(nextSlot)}
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="mt-5 grid gap-2 sm:grid-cols-2">
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="h-10 rounded-xl border-slate-300 hover:border-blue-300 hover:bg-blue-50"
                >
                  <Link href={`/interviewers/${person.interviewer_id}`}>
                    View profile
                  </Link>
                </Button>
                <Button
                  asChild
                  size="sm"
                  className="h-10 rounded-xl bg-blue-600 text-white hover:bg-blue-700"
                >
                  <Link
                    href={
                      nextSlot
                        ? authenticated
                          ? `/candidate?slot=${encodeURIComponent(nextSlot.id)}&interviewer=${encodeURIComponent(person.interviewer_id)}`
                          : `/login?next=${encodeURIComponent(`/candidate?slot=${encodeURIComponent(nextSlot.id)}&interviewer=${encodeURIComponent(person.interviewer_id)}`)}`
                        : `/interviewers/${person.interviewer_id}`
                    }
                  >
                    Book interview
                  </Link>
                </Button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function Filter({
  label,
  value,
  onChange,
  options,
  allLabel,
}: {
  label: string;
  value: string;
  onChange(value: string): void;
  options: string[];
  allLabel: string;
}) {
  return (
    <label className="space-y-1.5">
      <span className="block text-xs font-bold tracking-wide text-slate-500 uppercase">
        {label}
      </span>
      <select
        className="h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none focus:ring-2 focus:ring-blue-600"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="all">{allLabel}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}
