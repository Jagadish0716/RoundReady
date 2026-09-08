"use client";

import {
  BriefcaseBusiness,
  Check,
  FileText,
  Globe2,
  Linkedin,
  Mail,
  MapPin,
  Target,
  Trash2,
  UserRound,
} from "lucide-react";
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
import {
  CandidateProfileHelp,
  CandidateSidebar,
  ProfileHeader,
} from "@/components/candidate/candidate-profile-chrome";
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
function validExperienceInput(value: string): boolean {
  if (value === "") return true;
  if (!/^\d{1,2}(?:\.\d?)?$/.test(value)) return false;
  return Number(value) <= 20;
}
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
const formatFileSize = (bytes: number) =>
  bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;

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
  const completion = useMemo(() => {
    const complete = [
      profile.full_name.trim(),
      mobile,
      profile.city,
      profile.experience_years,
      profile.current_role,
      profile.target_role,
      profile.preferred_language,
      profile.linkedin_url,
      resumeFile ?? resume,
    ].filter(Boolean).length;
    return Math.round((complete / 9) * 100);
  }, [mobile, profile, resume, resumeFile]);
  const applyLoaded = useCallback(
    (loaded: CandidateProfile) => {
      const loadedProfile = toInput(loaded);
      if (!validExperienceInput(loadedProfile.experience_years)) {
        loadedProfile.experience_years = "";
        setErrors((current) => ({
          ...current,
          experience_years: "Experience must be between 0 and 20 years.",
        }));
      }
      setProfile(loadedProfile);
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
    if (
      profile.experience_years === "" ||
      !validExperienceInput(profile.experience_years) ||
      !Number.isFinite(years) ||
      years < 0 ||
      years > 20
    )
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
  const fieldInput = (
    field: Field,
    label: string,
    icon: typeof UserRound,
    type = "text",
    placeholder?: string,
    required = false,
  ) => {
    const Icon = icon;
    return (
      <div>
        <div className="flex items-center">
          <Label htmlFor={field}>{label}</Label>
          {required && (
            <span className="ml-1 text-red-600" aria-hidden="true">
              *
            </span>
          )}
        </div>
        <div className="relative mt-2">
          <Icon
            className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-500"
            aria-hidden="true"
          />
          <Input
            className="h-11 border-slate-300 pl-10"
            id={field}
            type={type}
            placeholder={placeholder}
            value={profile[field] ?? ""}
            required={required}
            disabled={saving}
            aria-invalid={Boolean(errors[field])}
            aria-describedby={errors[field] ? `${field}-error` : undefined}
            onChange={(event) => setField(field, event.target.value)}
          />
        </div>
        {errors[field] && (
          <p id={`${field}-error`} className="mt-1 text-sm text-red-700">
            {errors[field]}
          </p>
        )}
      </div>
    );
  };
  return (
    <section
      id="candidate-profile"
      className="grid min-w-0 gap-6 lg:grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[220px_minmax(0,1fr)_280px]"
      aria-label="Candidate profile dashboard"
    >
      <CandidateSidebar
        displayName={
          profile.full_name || accountEmail.split("@")[0] || "Candidate"
        }
      />
      <div className="min-w-0 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
        <ProfileHeader completion={completion} />
        <div className="mt-6 space-y-4">
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
        </div>
        <form
          className="mt-6 grid gap-x-7 gap-y-6 sm:grid-cols-2"
          onSubmit={submit}
          noValidate
        >
          <div className="sm:col-span-2">
            {fieldInput(
              "full_name",
              "Full name",
              UserRound,
              "text",
              undefined,
              true,
            )}
          </div>
          <div>
            <Label htmlFor="mobile">Phone number</Label>
            <div className="mt-2 flex min-w-0 gap-2">
              <input
                aria-label="Country code"
                list="country-codes"
                className="h-11 w-36 shrink-0 rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-600 sm:w-40"
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
                className="h-11 min-w-0"
                id="mobile"
                aria-label="Mobile number"
                inputMode="numeric"
                pattern="[0-9]*"
                value={mobile}
                disabled={saving}
                aria-invalid={Boolean(errors.phone)}
                aria-describedby={errors.phone ? "phone-error" : "phone-help"}
                onChange={(e) => {
                  setMobile(e.target.value.replace(/\D/g, ""));
                  setErrors((current) => ({ ...current, phone: undefined }));
                }}
              />
            </div>
            <p id="phone-help" className="mt-1 text-sm text-neutral-500">
              Select your country code and enter your mobile number.
            </p>
            {errors.phone && (
              <p id="phone-error" className="mt-1 text-sm text-red-700">
                {errors.phone}
              </p>
            )}
          </div>
          <div>
            <Label htmlFor="email">Email address</Label>
            <div className="relative mt-2">
              <Mail
                className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-500"
                aria-hidden="true"
              />
              <Input
                className="h-11 bg-slate-100 pl-10 text-slate-600"
                id="email"
                type="email"
                value={accountEmail}
                readOnly
                disabled
              />
            </div>
            <p className="mt-1 text-sm text-neutral-500">
              This is the email you used to sign up and cannot be changed.
            </p>
          </div>
          {fieldInput("city", "City", MapPin)}
          <div>
            <Label htmlFor="experience_years">Experience (years)</Label>
            <div className="relative mt-2">
              <BriefcaseBusiness
                className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-500"
                aria-hidden="true"
              />
              <Input
                className="h-11 border-slate-300 pl-10"
                id="experience_years"
                type="text"
                inputMode="decimal"
                value={profile.experience_years}
                disabled={saving}
                aria-invalid={Boolean(errors.experience_years)}
                aria-describedby={
                  errors.experience_years
                    ? "experience-error"
                    : "experience-help"
                }
                onChange={(event) => {
                  if (validExperienceInput(event.target.value))
                    setField("experience_years", event.target.value);
                }}
              />
            </div>
            <p id="experience-help" className="mt-1 text-sm text-neutral-500">
              Enter your total professional experience (0 – 20 years).
            </p>
            {errors.experience_years && (
              <p id="experience-error" className="mt-1 text-sm text-red-700">
                {errors.experience_years}
              </p>
            )}
          </div>
          {fieldInput("current_role", "Current role", BriefcaseBusiness)}
          {fieldInput("target_role", "Target role", Target)}
          <div>
            <Label htmlFor="preferred_language">Preferred language</Label>
            <div className="relative mt-2">
              <Globe2
                className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-500"
                aria-hidden="true"
              />
              <select
                id="preferred_language"
                className="h-11 w-full appearance-none rounded-md border border-slate-300 bg-white pr-3 pl-10 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                value={profile.preferred_language}
                disabled={saving}
                onChange={(e) => setField("preferred_language", e.target.value)}
              >
                {languages.map((language) => (
                  <option key={language}>{language}</option>
                ))}
              </select>
            </div>
          </div>
          {fieldInput(
            "linkedin_url",
            "LinkedIn URL",
            Linkedin,
            "url",
            "https://www.linkedin.com/in/your-profile",
          )}
          <div className="sm:col-span-2">
            <Label htmlFor="resume">Resume</Label>
            <label
              htmlFor="resume"
              className="mt-2 flex cursor-pointer flex-col items-start gap-4 rounded-lg border border-dashed border-slate-300 bg-slate-50/60 p-5 transition-colors focus-within:ring-2 focus-within:ring-blue-600 hover:border-blue-400 hover:bg-blue-50/40 sm:flex-row sm:items-center sm:justify-between"
            >
              <span className="flex items-center gap-4">
                <FileText
                  className="h-9 w-9 text-neutral-500"
                  aria-hidden="true"
                />
                <span>
                  <span className="block font-medium text-slate-900">
                    Upload your resume (PDF, DOC or DOCX)
                  </span>
                  <span className="text-sm text-neutral-500">
                    Maximum file size: 5 MB
                  </span>
                </span>
              </span>
              <span className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 shadow-sm">
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
            {resumeFile || resume ? (
              <div className="mt-3 flex items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white">
                    <Check className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <span className="truncate text-sm font-semibold text-slate-900">
                    {resumeFile?.name ?? resume?.file_name}
                  </span>
                  <span className="shrink-0 text-xs text-slate-500">
                    {formatFileSize(
                      resumeFile?.size ?? resume?.size_bytes ?? 0,
                    )}
                  </span>
                </div>
                {resumeFile ? (
                  <button
                    type="button"
                    className="rounded p-1 text-slate-600 hover:bg-emerald-100 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
                    aria-label={`Remove ${resumeFile.name}`}
                    onClick={() => setResumeFile(null)}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </button>
                ) : null}
              </div>
            ) : null}
            <p className="mt-2 text-sm text-neutral-500">
              Keep your resume updated to help interviewers understand your
              background.
            </p>
            {errors.resume && (
              <p className="mt-1 text-sm text-red-700">{errors.resume}</p>
            )}
          </div>
          <div className="border-t border-slate-100 pt-5 sm:col-span-2">
            <Button
              className="bg-blue-600 px-6 hover:bg-blue-700"
              type="submit"
              disabled={saving}
            >
              {saving ? "Saving…" : "Save profile"}
            </Button>
          </div>
        </form>
      </div>
      <div className="lg:col-start-2 xl:col-start-auto">
        <CandidateProfileHelp />
      </div>
    </section>
  );
}
