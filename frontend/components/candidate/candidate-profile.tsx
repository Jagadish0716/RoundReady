"use client";

import { FileText } from "lucide-react";
import {
  getCountries,
  getCountryCallingCode,
  parsePhoneNumberFromString,
  type CountryCode,
} from "libphonenumber-js";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiClientError } from "@/lib/api/client";
import {
  getCandidateProfile,
  getCandidateResume,
  saveCandidateProfile,
  uploadCandidateResume,
} from "@/lib/api/candidate-profile";
import type {
  CandidateProfile,
  CandidateProfileInput,
  ResumeMetadata,
} from "@/types/candidate-profile";

const languages = [
  "English",
  "Hindi",
  "Kannada",
  "Tamil",
  "Telugu",
  "Malayalam",
  "Marathi",
  "Bengali",
] as const;
const emptyProfile: CandidateProfileInput = {
  full_name: "",
  phone: null,
  city: null,
  experience_years: "0.0",
  current_role: null,
  target_role: null,
  preferred_language: "English",
  linkedin_url: null,
};
type Field = keyof CandidateProfileInput;
type Errors = Partial<Record<Field | "resume", string>>;
const nullable = (value: string) => value.trim() || null;
const toInput = (p: CandidateProfile): CandidateProfileInput => ({
  full_name: p.full_name,
  phone: p.phone,
  city: p.city,
  experience_years: p.experience_years,
  current_role: p.current_role,
  target_role: p.target_role,
  preferred_language: languages.includes(
    p.preferred_language as (typeof languages)[number],
  )
    ? p.preferred_language
    : "English",
  linkedin_url: p.linkedin_url,
});
function messageFor(error: unknown) {
  if (!(error instanceof ApiClientError)) return "Unable to save your profile.";
  if (error.status === 422)
    return "Some profile values are invalid. Review the form and try again.";
  if (error.status === 413) return "Resume must be 5 MB or smaller.";
  if (error.status === 403)
    return "You do not have access to candidate profiles.";
  return error.message;
}
const flag = (country: CountryCode) =>
  String.fromCodePoint(
    ...country.split("").map((letter) => 127397 + letter.charCodeAt(0)),
  );

export function CandidateProfileForm() {
  const { request, state } = useAuth();
  const accountEmail =
    state.status === "authenticated" ? state.session.user.email : "";
  const [profile, setProfile] = useState(emptyProfile);
  const [country, setCountry] = useState<CountryCode>("IN");
  const [countryQuery, setCountryQuery] = useState("India (+91)");
  const [mobile, setMobile] = useState("");
  const [resume, setResume] = useState<ResumeMetadata | null>(null);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [exists, setExists] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [notice, setNotice] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const displayNames = useMemo(
    () => new Intl.DisplayNames(["en"], { type: "region" }),
    [],
  );
  const countries = useMemo(
    () =>
      getCountries().map((code) => ({
        code,
        name: displayNames.of(code) ?? code,
        callingCode: getCountryCallingCode(code),
      })),
    [displayNames],
  );
  const applyLoaded = useCallback(
    (loaded: CandidateProfile) => {
      setProfile(toInput(loaded));
      setExists(true);
      if (loaded.phone) {
        const parsed = parsePhoneNumberFromString(loaded.phone);
        if (parsed) {
          const parsedCountry = parsed.country ?? "IN";
          setCountry(parsedCountry);
          setCountryQuery(
            `${displayNames.of(parsedCountry) ?? parsedCountry} (+${getCountryCallingCode(parsedCountry)})`,
          );
          setMobile(parsed.nationalNumber);
        }
      }
    },
    [displayNames],
  );
  const load = useCallback(async () => {
    setLoading(true);
    setApiError(null);
    const [profileResult, resumeResult] = await Promise.allSettled([
      getCandidateProfile(request),
      getCandidateResume(request),
    ]);
    if (profileResult.status === "fulfilled") applyLoaded(profileResult.value);
    else if (
      profileResult.reason instanceof ApiClientError &&
      profileResult.reason.status === 404
    ) {
      setProfile(emptyProfile);
      setExists(false);
    } else setApiError(messageFor(profileResult.reason));
    if (resumeResult.status === "fulfilled") setResume(resumeResult.value);
    setLoading(false);
  }, [applyLoaded, request]);
  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);
  function setField(field: Field, value: string) {
    setProfile((current) => ({
      ...current,
      [field]:
        field === "full_name" ||
        field === "preferred_language" ||
        field === "experience_years"
          ? value
          : nullable(value),
    }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    setNotice(null);
  }
  function chooseResume(file?: File) {
    if (!file) return;
    const extension = file.name.split(".").pop()?.toLowerCase();
    const error = !["pdf", "doc", "docx"].includes(extension ?? "")
      ? "Choose a PDF, DOC, or DOCX file."
      : file.size > 5 * 1024 * 1024
        ? "Resume must be 5 MB or smaller."
        : undefined;
    setErrors((current) => ({ ...current, resume: error }));
    setResumeFile(error ? null : file);
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation: Errors = {};
    if (!profile.full_name.trim())
      validation.full_name = "Full name is required.";
    const years = Number(profile.experience_years);
    if (!Number.isFinite(years) || years < 0 || years > 20)
      validation.experience_years =
        "Experience must be between 0 and 20 years.";
    let phone: string | null = null;
    if (mobile) {
      const parsed = parsePhoneNumberFromString(mobile, country);
      if (!parsed?.isValid()) validation.phone = "Enter a valid mobile number.";
      else phone = parsed.number;
    }
    if (profile.linkedin_url) {
      try {
        const host = new URL(profile.linkedin_url).hostname;
        if (host !== "linkedin.com" && !host.endsWith(".linkedin.com"))
          validation.linkedin_url = "Use a linkedin.com URL.";
      } catch {
        validation.linkedin_url = "Enter a valid URL.";
      }
    }
    setErrors(validation);
    setApiError(null);
    setNotice(null);
    if (Object.keys(validation).length) return;
    setSaving(true);
    try {
      const saved = await saveCandidateProfile(request, {
        ...profile,
        full_name: profile.full_name.trim(),
        phone,
      });
      applyLoaded(saved);
      if (resumeFile) {
        setResume(await uploadCandidateResume(request, resumeFile));
        setResumeFile(null);
      }
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
  const fieldInput = (field: Field, label: string, type = "text") => (
    <div>
      <Label htmlFor={field}>{label}</Label>
      <Input
        className="mt-2"
        id={field}
        type={type}
        value={profile[field] ?? ""}
        disabled={saving}
        aria-invalid={Boolean(errors[field])}
        onChange={(event) => setField(field, event.target.value)}
      />
      {errors[field] && (
        <p className="mt-1 text-sm text-red-700">{errors[field]}</p>
      )}
    </div>
  );
  return (
    <section className="w-full max-w-5xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">
          Candidate profile
        </h1>
        <p className="mt-1 text-base text-neutral-600">
          Create your profile to get ready for interviews.
        </p>
      </div>
      {notice && (
        <p
          role="status"
          className="rounded-md bg-green-50 p-3 text-sm text-green-800"
        >
          {notice}
        </p>
      )}
      {apiError && (
        <p
          role="alert"
          className="rounded-md bg-red-50 p-3 text-sm text-red-800"
        >
          {apiError}
        </p>
      )}
      <form
        className="grid gap-x-8 gap-y-6 sm:grid-cols-2"
        onSubmit={submit}
        noValidate
      >
        <div className="sm:col-span-2">
          {fieldInput("full_name", "Full name")}
        </div>
        <div>
          <Label htmlFor="mobile">Phone number</Label>
          <div className="mt-2 flex gap-2">
            <input
              aria-label="Country code"
              list="country-codes"
              className="h-10 max-w-40 rounded-md border border-neutral-300 bg-white px-2 text-sm"
              value={countryQuery}
              disabled={saving}
              onChange={(event) => {
                setCountryQuery(event.target.value);
                const match = countries.find(
                  (item) =>
                    `${item.name} (+${item.callingCode})` ===
                    event.target.value,
                );
                if (match) setCountry(match.code);
              }}
            />
            <datalist id="country-codes">
              {countries.map((item) => (
                <option
                  key={item.code}
                  value={`${item.name} (+${item.callingCode})`}
                >
                  {flag(item.code)}
                </option>
              ))}
            </datalist>
            <Input
              id="mobile"
              aria-label="Mobile number"
              inputMode="numeric"
              pattern="[0-9]*"
              value={mobile}
              disabled={saving}
              onChange={(e) => {
                setMobile(e.target.value.replace(/\D/g, ""));
                setErrors((current) => ({ ...current, phone: undefined }));
              }}
            />
          </div>
          <p className="mt-1 text-sm text-neutral-500">
            Select your country code and enter your mobile number.
          </p>
          {errors.phone && (
            <p className="mt-1 text-sm text-red-700">{errors.phone}</p>
          )}
        </div>
        <div>
          <Label htmlFor="email">Profile email</Label>
          <Input
            className="mt-2 bg-neutral-100"
            id="email"
            type="email"
            value={accountEmail}
            readOnly
            disabled
          />
          <p className="mt-1 text-sm text-neutral-500">
            This is the email you used to sign up and cannot be changed.
          </p>
        </div>
        {fieldInput("city", "City")}
        <div>
          <Label htmlFor="experience_years">Experience (years)</Label>
          <Input
            className="mt-2"
            id="experience_years"
            type="number"
            min="0"
            max="20"
            step="0.1"
            value={profile.experience_years}
            disabled={saving}
            aria-invalid={Boolean(errors.experience_years)}
            onChange={(e) => setField("experience_years", e.target.value)}
          />
          <p className="mt-1 text-sm text-neutral-500">
            Enter your total professional experience (0 – 20 years).
          </p>
          {errors.experience_years && (
            <p className="mt-1 text-sm text-red-700">
              {errors.experience_years}
            </p>
          )}
        </div>
        {fieldInput("current_role", "Current role")}
        {fieldInput("target_role", "Target role")}
        <div>
          <Label htmlFor="preferred_language">Preferred language</Label>
          <select
            id="preferred_language"
            className="mt-2 h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm"
            value={profile.preferred_language}
            disabled={saving}
            onChange={(e) => setField("preferred_language", e.target.value)}
          >
            {languages.map((language) => (
              <option key={language}>{language}</option>
            ))}
          </select>
        </div>
        {fieldInput("linkedin_url", "LinkedIn URL", "url")}
        <div className="sm:col-span-2">
          <Label htmlFor="resume">Resume</Label>
          <label
            htmlFor="resume"
            className="mt-2 flex cursor-pointer items-center justify-between rounded-md border border-dashed border-neutral-300 p-5"
          >
            <span className="flex items-center gap-4">
              <FileText
                className="h-9 w-9 text-neutral-500"
                aria-hidden="true"
              />
              <span>
                <span className="block font-medium">
                  {resumeFile?.name ??
                    resume?.file_name ??
                    "Upload your resume (PDF, DOC or DOCX)"}
                </span>
                <span className="text-sm text-neutral-500">
                  Maximum file size: 5 MB
                </span>
              </span>
            </span>
            <span className="rounded-md border border-neutral-300 bg-white px-4 py-2 text-sm font-medium">
              Choose file
            </span>
          </label>
          <input
            className="sr-only"
            id="resume"
            type="file"
            accept=".pdf,.doc,.docx"
            disabled={saving}
            onChange={(e) => chooseResume(e.target.files?.[0])}
          />
          <p className="mt-2 text-sm text-neutral-500">
            Keep your resume updated to help interviewers understand your
            background.
          </p>
          {errors.resume && (
            <p className="mt-1 text-sm text-red-700">{errors.resume}</p>
          )}
        </div>
        <div className="sm:col-span-2">
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save profile"}
          </Button>
        </div>
      </form>
    </section>
  );
}
