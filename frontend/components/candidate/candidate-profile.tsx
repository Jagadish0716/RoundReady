"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiClientError } from "@/lib/api/client";
import {
  getCandidateProfile,
  saveCandidateProfile,
} from "@/lib/api/candidate-profile";
import type {
  CandidateProfile,
  CandidateProfileInput,
} from "@/types/candidate-profile";

const emptyProfile: CandidateProfileInput = {
  full_name: "",
  phone: null,
  email: null,
  city: null,
  experience_years: "0.0",
  current_role: null,
  target_role: null,
  preferred_language: "English",
  linkedin_url: null,
  resume_url: null,
};

type Field = keyof CandidateProfileInput;
type Errors = Partial<Record<Field, string>>;

function inputValue(value: string | null): string {
  return value ?? "";
}

function nullable(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function toInput(profile: CandidateProfile): CandidateProfileInput {
  return {
    full_name: profile.full_name,
    phone: profile.phone,
    email: profile.email,
    city: profile.city,
    experience_years: profile.experience_years,
    current_role: profile.current_role,
    target_role: profile.target_role,
    preferred_language: profile.preferred_language,
    linkedin_url: profile.linkedin_url,
    resume_url: profile.resume_url,
  };
}

function validate(profile: CandidateProfileInput): Errors {
  const errors: Errors = {};
  if (!profile.full_name.trim()) errors.full_name = "Full name is required.";
  if (profile.full_name.trim().length > 160)
    errors.full_name = "Full name must be 160 characters or fewer.";
  if (profile.phone && !/^\+[1-9]\d{7,14}$/.test(profile.phone))
    errors.phone = "Use international format, for example +919876543210.";
  const years = Number(profile.experience_years);
  if (!Number.isFinite(years) || years < 0 || years > 60)
    errors.experience_years = "Experience must be between 0 and 60 years.";
  if (!profile.preferred_language.trim())
    errors.preferred_language = "Preferred language is required.";
  if (profile.linkedin_url) {
    try {
      const host = new URL(profile.linkedin_url).hostname;
      if (host !== "linkedin.com" && !host.endsWith(".linkedin.com"))
        errors.linkedin_url = "Use a linkedin.com URL.";
    } catch {
      errors.linkedin_url = "Enter a valid URL.";
    }
  }
  return errors;
}

function messageFor(error: unknown): string {
  if (!(error instanceof ApiClientError)) return "Unable to save your profile.";
  if (error.status === 422)
    return "Some profile values are invalid. Review the form and try again.";
  if (error.status === 403)
    return "You do not have access to candidate profiles.";
  return error.message;
}

export function CandidateProfileForm() {
  const { request } = useAuth();
  const [profile, setProfile] = useState<CandidateProfileInput>(emptyProfile);
  const [exists, setExists] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [notice, setNotice] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setApiError(null);
    try {
      const loaded = await getCandidateProfile(request);
      setProfile(toInput(loaded));
      setExists(true);
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 404) {
        setProfile(emptyProfile);
        setExists(false);
      } else {
        setApiError(messageFor(error));
      }
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    let active = true;
    getCandidateProfile(request)
      .then((loaded) => {
        if (!active) return;
        setProfile(toInput(loaded));
        setExists(true);
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (error instanceof ApiClientError && error.status === 404) {
          setProfile(emptyProfile);
          setExists(false);
        } else {
          setApiError(messageFor(error));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [request]);

  function setField(field: Field, value: string) {
    setProfile((current) => ({
      ...current,
      [field]:
        field === "full_name" || field === "preferred_language"
          ? value
          : nullable(value),
    }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    setNotice(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validate(profile);
    setErrors(validation);
    setApiError(null);
    setNotice(null);
    if (Object.keys(validation).length) return;
    setSaving(true);
    try {
      const saved = await saveCandidateProfile(request, {
        ...profile,
        full_name: profile.full_name.trim(),
        preferred_language: profile.preferred_language.trim(),
      });
      setProfile(toInput(saved));
      setExists(true);
      setNotice("Profile saved successfully.");
    } catch (error) {
      setApiError(messageFor(error));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p role="status">Loading your profile…</p>;
  if (apiError && !exists)
    return (
      <div className="space-y-3">
        <p role="alert" className="text-sm text-red-700">
          {apiError}
        </p>
        <Button type="button" variant="outline" onClick={() => void load()}>
          Try again
        </Button>
      </div>
    );

  const fields: Array<{
    field: Field;
    label: string;
    type?: string;
    placeholder?: string;
  }> = [
    { field: "full_name", label: "Full name" },
    {
      field: "phone",
      label: "Phone",
      type: "tel",
      placeholder: "+919876543210",
    },
    { field: "email", label: "Profile email", type: "email" },
    { field: "city", label: "City" },
    { field: "experience_years", label: "Experience (years)", type: "number" },
    { field: "current_role", label: "Current role" },
    { field: "target_role", label: "Target role" },
    { field: "preferred_language", label: "Preferred language" },
    { field: "linkedin_url", label: "LinkedIn URL", type: "url" },
    { field: "resume_url", label: "Resume URL", type: "url" },
  ];

  return (
    <section className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Candidate profile</h1>
        <p className="mt-1 text-sm text-neutral-600">
          {exists
            ? "Keep your interview profile current."
            : "Create your profile to get ready for interviews."}
        </p>
      </div>
      {notice ? (
        <p
          role="status"
          className="rounded-md bg-green-50 p-3 text-sm text-green-800"
        >
          {notice}
        </p>
      ) : null}
      {apiError ? (
        <p
          role="alert"
          className="rounded-md bg-red-50 p-3 text-sm text-red-800"
        >
          {apiError}
        </p>
      ) : null}
      <form className="grid gap-5 sm:grid-cols-2" onSubmit={submit} noValidate>
        {fields.map(({ field, label, type = "text", placeholder }) => (
          <div
            className={field === "full_name" ? "sm:col-span-2" : ""}
            key={field}
          >
            <Label htmlFor={field}>{label}</Label>
            <Input
              className="mt-2"
              id={field}
              type={type}
              placeholder={placeholder}
              value={inputValue(profile[field])}
              min={field === "experience_years" ? "0" : undefined}
              max={field === "experience_years" ? "60" : undefined}
              step={field === "experience_years" ? "0.1" : undefined}
              disabled={saving}
              aria-invalid={Boolean(errors[field])}
              onChange={(event) => setField(field, event.target.value)}
            />
            {errors[field] ? (
              <p className="mt-1 text-sm text-red-700">{errors[field]}</p>
            ) : null}
          </div>
        ))}
        <div className="sm:col-span-2">
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save profile"}
          </Button>
        </div>
      </form>
    </section>
  );
}
