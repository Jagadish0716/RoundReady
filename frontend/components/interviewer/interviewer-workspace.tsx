"use client";

import { useEffect, useState, type FormEvent } from "react";

import { VerificationStatusCard } from "@/components/interviewer/verification-status";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiClientError } from "@/lib/api/client";
import * as api from "@/lib/api/interviewer";
import {
  interviewerDomains,
  type Blockout,
  type InterviewerProfile,
  type InterviewerProfileInput,
  type InterviewerSkillInput,
  type WeeklyRuleInput,
} from "@/types/interviewer";

const emptyProfile: InterviewerProfileInput = {
  headline: "",
  company: null,
  job_title: null,
  experience_years: "0.0",
  linkedin_url: null,
  github_url: null,
  bio: null,
};
const emptySkill: InterviewerSkillInput = {
  domain: "Backend",
  topic: "",
  skill_name: "",
  experience_years: "0.0",
};
const emptyRule: WeeklyRuleInput = {
  weekday: 1,
  start_time: "18:00",
  end_time: "20:00",
  timezone: "Asia/Kolkata",
};

function nullable(value: string): string | null {
  return value.trim() || null;
}

function profileInput(value: InterviewerProfile): InterviewerProfileInput {
  return {
    headline: value.headline,
    company: value.company,
    job_title: value.job_title,
    experience_years: value.experience_years,
    linkedin_url: value.linkedin_url,
    github_url: value.github_url,
    bio: value.bio,
  };
}

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiClientError))
    return "The request could not be completed.";
  if (error.status === 422)
    return "Some values are invalid. Review them and try again.";
  if (error.status === 403)
    return "You do not have access to interviewer settings.";
  return error.message;
}

export function InterviewerWorkspace() {
  const { request } = useAuth();
  const [profile, setProfile] = useState<InterviewerProfileInput>(emptyProfile);
  const [savedProfile, setSavedProfile] = useState<InterviewerProfile | null>(
    null,
  );
  const [skills, setSkills] = useState<InterviewerSkillInput[]>([]);
  const [rules, setRules] = useState<WeeklyRuleInput[]>([]);
  const [blockouts, setBlockouts] = useState<Blockout[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.getInterviewerProfile(request),
      api.getSkills(request),
      api.getWeeklyRules(request),
      api.getBlockouts(request),
    ]).then(([profileResult, skillsResult, rulesResult, blockoutsResult]) => {
      if (!active) return;
      if (profileResult.status === "fulfilled") {
        setSavedProfile(profileResult.value);
        setProfile(profileInput(profileResult.value));
      } else if (!(
        profileResult.reason instanceof ApiClientError &&
        profileResult.reason.status === 404
      )) {
        setError(errorMessage(profileResult.reason));
      }
      if (skillsResult.status === "fulfilled") setSkills(skillsResult.value);
      if (rulesResult.status === "fulfilled") setRules(rulesResult.value);
      if (blockoutsResult.status === "fulfilled")
        setBlockouts(blockoutsResult.value);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [request]);

  function feedback(message: string) {
    setError(null);
    setNotice(message);
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);
    if (!profile.headline.trim()) return setError("Headline is required.");
    const years = Number(profile.experience_years);
    if (!Number.isFinite(years) || years < 0 || years > 60)
      return setError("Experience must be between 0 and 60 years.");
    setSaving("profile");
    try {
      const saved = await api.saveInterviewerProfile(request, {
        ...profile,
        headline: profile.headline.trim(),
      });
      setSavedProfile(saved);
      setProfile(profileInput(saved));
      feedback("Professional profile saved.");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSaving(null);
    }
  }

  async function saveSkills() {
    if (skills.some((item) => !item.topic.trim() || !item.skill_name.trim()))
      return setError("Every skill needs a topic and skill name.");
    setSaving("skills");
    setNotice(null);
    try {
      const saved = await api.saveSkills(request, skills);
      setSkills(saved);
      feedback("Skills saved.");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSaving(null);
    }
  }

  async function saveRules() {
    if (rules.some((rule) => rule.start_time >= rule.end_time))
      return setError("Availability start time must be before end time.");
    setSaving("rules");
    setNotice(null);
    try {
      const saved = await api.saveWeeklyRules(request, rules);
      setRules(saved);
      feedback("Weekly availability saved.");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSaving(null);
    }
  }

  async function addBlockout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const starts = String(data.get("starts_at"));
    const ends = String(data.get("ends_at"));
    if (!starts || !ends || new Date(starts) >= new Date(ends))
      return setError("Blockout start must be before end.");
    setSaving("blockout");
    setNotice(null);
    try {
      await api.createBlockout(request, {
        starts_at: new Date(starts).toISOString(),
        ends_at: new Date(ends).toISOString(),
        reason: nullable(String(data.get("reason") ?? "")),
      });
      setBlockouts(await api.getBlockouts(request));
      form.reset();
      feedback("Blockout added.");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSaving(null);
    }
  }

  async function removeBlockout(id: string) {
    setSaving(`blockout-${id}`);
    setNotice(null);
    try {
      await api.deleteBlockout(request, id);
      setBlockouts(await api.getBlockouts(request));
      feedback("Blockout removed.");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSaving(null);
    }
  }

  if (loading)
    return <p role="status">Loading interviewer profile and availability…</p>;

  return (
    <div className="max-w-4xl space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">Interviewer profile</h1>
        <p className="mt-1 text-sm text-neutral-600">
          Manage your professional details and interview availability.
        </p>
      </header>
      {error ? (
        <p
          role="alert"
          className="rounded-md bg-red-50 p-3 text-sm text-red-800"
        >
          {error}
        </p>
      ) : null}
      {notice ? (
        <p
          role="status"
          className="rounded-md bg-green-50 p-3 text-sm text-green-800"
        >
          {notice}
        </p>
      ) : null}
      {savedProfile ? (
        <VerificationStatusCard
          status={savedProfile.verification_status}
          reason={savedProfile.verification_reason}
        />
      ) : (
        <p className="rounded-md border border-dashed p-4 text-sm">
          Create your professional profile to begin verification.
        </p>
      )}

      <form
        className="grid gap-4 rounded-lg border bg-white p-5 sm:grid-cols-2"
        onSubmit={saveProfile}
        noValidate
      >
        <h2 className="text-lg font-semibold sm:col-span-2">
          Professional details
        </h2>
        {(
          [
            ["headline", "Headline", "text"],
            ["company", "Company", "text"],
            ["job_title", "Job title", "text"],
            ["experience_years", "Experience (years)", "number"],
            ["linkedin_url", "LinkedIn URL", "url"],
            ["github_url", "GitHub URL", "url"],
          ] as const
        ).map(([field, label, type]) => (
          <div key={field}>
            <Label htmlFor={field}>{label}</Label>
            <Input
              className="mt-2"
              id={field}
              type={type}
              step={type === "number" ? "0.1" : undefined}
              min={type === "number" ? "0" : undefined}
              max={type === "number" ? "60" : undefined}
              value={profile[field] ?? ""}
              disabled={saving === "profile"}
              onChange={(event) =>
                setProfile((current) => ({
                  ...current,
                  [field]:
                    field === "headline" || field === "experience_years"
                      ? event.target.value
                      : nullable(event.target.value),
                }))
              }
            />
          </div>
        ))}
        <div className="sm:col-span-2">
          <Label htmlFor="bio">Bio</Label>
          <textarea
            id="bio"
            className="mt-2 min-h-28 w-full rounded-md border border-neutral-300 p-3 text-sm"
            maxLength={4000}
            value={profile.bio ?? ""}
            disabled={saving === "profile"}
            onChange={(event) =>
              setProfile((current) => ({
                ...current,
                bio: nullable(event.target.value),
              }))
            }
          />
        </div>
        <div className="sm:col-span-2">
          <Button type="submit" disabled={saving !== null}>
            {saving === "profile" ? "Saving…" : "Save profile"}
          </Button>
        </div>
      </form>

      <section className="space-y-4 rounded-lg border bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Skills and domains</h2>
          <Button
            type="button"
            variant="outline"
            onClick={() => setSkills((items) => [...items, { ...emptySkill }])}
          >
            Add skill
          </Button>
        </div>
        {skills.length === 0 ? (
          <p className="text-sm text-neutral-600">No skills added.</p>
        ) : (
          skills.map((skill, index) => (
            <div
              className="grid gap-2 rounded-md border p-3 sm:grid-cols-5"
              key={index}
            >
              <select
                aria-label={`Domain ${index + 1}`}
                className="h-10 rounded-md border px-2 text-sm"
                value={skill.domain}
                onChange={(event) =>
                  setSkills((items) =>
                    items.map((item, i) =>
                      i === index
                        ? {
                            ...item,
                            domain: event.target
                              .value as InterviewerSkillInput["domain"],
                          }
                        : item,
                    ),
                  )
                }
              >
                {interviewerDomains.map((domain) => (
                  <option key={domain}>{domain}</option>
                ))}
              </select>
              <Input
                aria-label={`Topic ${index + 1}`}
                placeholder="Topic"
                value={skill.topic}
                onChange={(event) =>
                  setSkills((items) =>
                    items.map((item, i) =>
                      i === index
                        ? { ...item, topic: event.target.value }
                        : item,
                    ),
                  )
                }
              />
              <Input
                aria-label={`Skill ${index + 1}`}
                placeholder="Skill"
                value={skill.skill_name}
                onChange={(event) =>
                  setSkills((items) =>
                    items.map((item, i) =>
                      i === index
                        ? { ...item, skill_name: event.target.value }
                        : item,
                    ),
                  )
                }
              />
              <Input
                aria-label={`Skill experience ${index + 1}`}
                type="number"
                min="0"
                max="60"
                step="0.1"
                value={skill.experience_years}
                onChange={(event) =>
                  setSkills((items) =>
                    items.map((item, i) =>
                      i === index
                        ? { ...item, experience_years: event.target.value }
                        : item,
                    ),
                  )
                }
              />
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  setSkills((items) => items.filter((_, i) => i !== index))
                }
              >
                Remove
              </Button>
            </div>
          ))
        )}
        <Button
          type="button"
          disabled={saving !== null}
          onClick={() => void saveSkills()}
        >
          {saving === "skills" ? "Saving…" : "Save skills"}
        </Button>
      </section>

      <section className="space-y-4 rounded-lg border bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Weekly availability</h2>
          <Button
            type="button"
            variant="outline"
            onClick={() => setRules((items) => [...items, { ...emptyRule }])}
          >
            Add time
          </Button>
        </div>
        {rules.length === 0 ? (
          <p className="text-sm text-neutral-600">
            No weekly availability set.
          </p>
        ) : (
          rules.map((rule, index) => (
            <div
              className="grid gap-2 rounded-md border p-3 sm:grid-cols-5"
              key={index}
            >
              <select
                aria-label={`Weekday ${index + 1}`}
                className="h-10 rounded-md border px-2 text-sm"
                value={rule.weekday}
                onChange={(event) =>
                  setRules((items) =>
                    items.map((item, i) =>
                      i === index
                        ? { ...item, weekday: Number(event.target.value) }
                        : item,
                    ),
                  )
                }
              >
                {[
                  "Monday",
                  "Tuesday",
                  "Wednesday",
                  "Thursday",
                  "Friday",
                  "Saturday",
                  "Sunday",
                ].map((day, i) => (
                  <option value={i} key={day}>
                    {day}
                  </option>
                ))}
              </select>
              <Input
                aria-label={`Start time ${index + 1}`}
                type="time"
                value={rule.start_time}
                onChange={(event) =>
                  setRules((items) =>
                    items.map((item, i) =>
                      i === index
                        ? { ...item, start_time: event.target.value }
                        : item,
                    ),
                  )
                }
              />
              <Input
                aria-label={`End time ${index + 1}`}
                type="time"
                value={rule.end_time}
                onChange={(event) =>
                  setRules((items) =>
                    items.map((item, i) =>
                      i === index
                        ? { ...item, end_time: event.target.value }
                        : item,
                    ),
                  )
                }
              />
              <Input
                aria-label={`Timezone ${index + 1}`}
                value={rule.timezone}
                onChange={(event) =>
                  setRules((items) =>
                    items.map((item, i) =>
                      i === index
                        ? { ...item, timezone: event.target.value }
                        : item,
                    ),
                  )
                }
              />
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  setRules((items) => items.filter((_, i) => i !== index))
                }
              >
                Remove
              </Button>
            </div>
          ))
        )}
        <Button
          type="button"
          disabled={saving !== null}
          onClick={() => void saveRules()}
        >
          {saving === "rules" ? "Saving…" : "Save availability"}
        </Button>
      </section>

      <section className="space-y-4 rounded-lg border bg-white p-5">
        <h2 className="text-lg font-semibold">Blockouts</h2>
        <form className="grid gap-3 sm:grid-cols-4" onSubmit={addBlockout}>
          <div>
            <Label htmlFor="starts_at">Starts</Label>
            <Input
              className="mt-2"
              id="starts_at"
              name="starts_at"
              type="datetime-local"
              required
            />
          </div>
          <div>
            <Label htmlFor="ends_at">Ends</Label>
            <Input
              className="mt-2"
              id="ends_at"
              name="ends_at"
              type="datetime-local"
              required
            />
          </div>
          <div>
            <Label htmlFor="reason">Reason</Label>
            <Input className="mt-2" id="reason" name="reason" />
          </div>
          <div className="self-end">
            <Button type="submit" disabled={saving !== null}>
              {saving === "blockout" ? "Adding…" : "Add blockout"}
            </Button>
          </div>
        </form>
        {blockouts.length === 0 ? (
          <p className="text-sm text-neutral-600">No blockouts.</p>
        ) : (
          <ul className="space-y-2">
            {blockouts.map((item) => (
              <li
                className="flex items-center justify-between rounded-md border p-3 text-sm"
                key={item.id}
              >
                <span>
                  {new Date(item.starts_at).toLocaleString()} –{" "}
                  {new Date(item.ends_at).toLocaleString()}
                  {item.reason ? ` · ${item.reason}` : ""}
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={saving !== null}
                  onClick={() => void removeBlockout(item.id)}
                >
                  Delete
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
