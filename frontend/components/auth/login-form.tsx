"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowRight,
  BadgeCheck,
  BarChart3,
  BriefcaseBusiness,
  HeartHandshake,
  IndianRupee,
  ShieldCheck,
  UserRound,
  UsersRound,
} from "lucide-react";

import { Logo } from "@/components/brand/logo";
import { authErrorMessage } from "@/components/auth/auth-error";
import { PasswordField } from "@/components/auth/password-field";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { redirectForRole } from "@/lib/auth/redirect";
import * as authApi from "@/lib/auth/api";
import { ApiClientError } from "@/lib/api/client";
import {
  validateCredentials,
  type CredentialsErrors,
} from "@/lib/auth/validation";
import type { RegistrationRole } from "@/types/auth";

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const search = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<CredentialsErrors>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [verificationRequired, setVerificationRequired] = useState(false);
  const [resendStatus, setResendStatus] = useState<string | null>(null);
  const [role, setRole] = useState<RegistrationRole>("candidate");
  const requested = search.get("next");
  const registerHref = requested
    ? `/register?next=${encodeURIComponent(requested)}`
    : "/register";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validateCredentials(email, password);
    setErrors(validation);
    setApiError(null);
    if (Object.keys(validation).length) return;
    setSubmitting(true);
    try {
      const user = await login(email.trim(), password);
      router.replace(redirectForRole(user.role, search.get("next")));
    } catch (error) {
      setVerificationRequired(
        error instanceof ApiClientError &&
          error.code === "email_verification_required",
      );
      setApiError(authErrorMessage(error, "login"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,#eef4ff_0,transparent_38%),linear-gradient(135deg,#ffffff_0%,#f8fafc_100%)] px-4 py-5 text-slate-950 sm:px-7 lg:px-10">
      <div className="mx-auto grid min-h-[calc(100vh-2.5rem)] max-w-[1480px] gap-7 lg:grid-cols-[minmax(0,1.08fr)_minmax(430px,0.72fr)] lg:items-stretch">
        <section className="order-2 overflow-hidden rounded-[2rem] border border-blue-100 bg-blue-50/80 lg:order-1">
          <div className="relative flex h-full flex-col p-7 sm:p-10 lg:min-h-[680px] lg:p-12">
            <div
              aria-hidden="true"
              className="absolute inset-0 bg-cover bg-center opacity-[0.13]"
              style={{
                backgroundImage: "url('/images/auth/candidate-login.jpg')",
              }}
            />
            <div
              aria-hidden="true"
              className="absolute inset-0 bg-gradient-to-br from-white/95 via-blue-50/90 to-blue-100/65"
            />

            <div className="relative z-10">
              <Link
                href="/"
                aria-label="RoundReady home"
                className="inline-flex rounded-md focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
              >
                <Logo variant="horizontal" priority className="w-[210px]" />
              </Link>
              <p className="mt-1 text-xs font-medium tracking-wide text-slate-600">
                Practice Today. Perform Tomorrow.
              </p>

              <div className="mt-12 max-w-2xl lg:mt-16">
                <h2 className="text-4xl leading-[1.05] font-bold tracking-tight sm:text-5xl xl:text-6xl">
                  Real practice.
                  <span className="block text-blue-600">Real progress.</span>
                </h2>
                <p className="mt-5 max-w-xl text-base leading-7 text-slate-700 sm:text-lg">
                  Practice with real tech professionals, get practical feedback,
                  and build the confidence you need for your next opportunity.
                </p>
              </div>

              <div className="mt-9 grid gap-5">
                <AuthBenefit
                  icon={<UsersRound aria-hidden />}
                  tone="emerald"
                  title="Verified interviewers"
                  text="Learn from experienced tech professionals"
                />
                <AuthBenefit
                  icon={<BarChart3 aria-hidden />}
                  tone="blue"
                  title="Practical feedback"
                  text="Understand your strengths and preparation gaps"
                />
                <AuthBenefit
                  icon={<IndianRupee aria-hidden />}
                  tone="rose"
                  title="Affordable access"
                  text="Just ₹200 per interview"
                />
              </div>
            </div>

            <blockquote className="relative z-10 mt-auto max-w-xl rounded-2xl border border-white/80 bg-white/80 p-6 shadow-sm backdrop-blur-sm">
              <p className="text-sm leading-6 text-slate-700 sm:text-base">
                “I failed several interviews while moving from Civil Engineering
                into IT because I lacked proper guidance. RoundReady is my way
                of helping others prepare better and avoid the same struggle.”
              </p>
              <footer className="mt-4 text-sm">
                <span className="font-semibold text-slate-950">— Jagadish</span>
                <span className="ml-2 text-slate-600">Founder, RoundReady</span>
              </footer>
            </blockquote>
          </div>
        </section>

        <section className="order-1 flex flex-col lg:order-2">
          <div className="mb-5 flex items-center justify-between gap-4 px-2">
            <Link
              href="/"
              aria-label="RoundReady home"
              className="rounded-md focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none lg:hidden"
            >
              <Logo variant="horizontal" priority className="w-[170px]" />
            </Link>
            <p className="ml-auto text-sm text-slate-600">
              New here?{" "}
              <Link className="font-semibold text-blue-700" href={registerHref}>
                Create an account
              </Link>
            </p>
          </div>

          <div className="flex flex-1 items-center">
            <form
              className="w-full rounded-[1.75rem] border border-slate-200/80 bg-white p-6 shadow-[0_20px_60px_-35px_rgba(15,23,42,0.32)] sm:p-10 lg:p-12"
              onSubmit={submit}
              noValidate
            >
              <div>
                <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                  Welcome back
                </h1>
                <p className="mt-2 text-slate-600">
                  {requested && role === "candidate"
                    ? "Sign in to continue booking your interview."
                    : `Sign in to your RoundReady ${role} account.`}
                </p>
              </div>

              <fieldset className="mt-8">
                <legend className="sr-only">Choose account type</legend>
                <div className="grid grid-cols-2 rounded-xl bg-slate-100 p-1">
                  <RoleButton
                    active={role === "candidate"}
                    icon={<UserRound aria-hidden />}
                    label="Candidate"
                    onClick={() => setRole("candidate")}
                    disabled={submitting}
                  />
                  <RoleButton
                    active={role === "interviewer"}
                    icon={<BriefcaseBusiness aria-hidden />}
                    label="Interviewer"
                    onClick={() => setRole("interviewer")}
                    disabled={submitting}
                  />
                </div>
              </fieldset>

              <div className="mt-7 space-y-5">
                {search.get("registered") === "1" ? (
                  <p
                    role="status"
                    className="rounded-md bg-green-50 p-3 text-sm text-green-800"
                  >
                    Account created. Sign in to continue.
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
                {verificationRequired ? (
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={async () => {
                      await authApi.resendVerification(email.trim(), requested);
                      setResendStatus(
                        "If the account still requires verification, a verification email has been sent.",
                      );
                    }}
                  >
                    Resend verification email
                  </Button>
                ) : null}
                {resendStatus ? (
                  <p role="status" className="text-sm text-neutral-600">
                    {resendStatus}
                  </p>
                ) : null}
                <div className="space-y-2">
                  <Label htmlFor="email">Email address</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    className="h-12"
                    value={email}
                    disabled={submitting}
                    aria-invalid={Boolean(errors.email)}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                  {errors.email ? (
                    <p className="text-sm text-red-700">{errors.email}</p>
                  ) : null}
                </div>
                <PasswordField
                  id="password"
                  label="Password"
                  value={password}
                  error={errors.password}
                  disabled={submitting}
                  onChange={setPassword}
                />
                <Button
                  className="h-12 w-full bg-blue-600 text-base hover:bg-blue-700 focus-visible:ring-blue-600"
                  type="submit"
                  disabled={submitting}
                >
                  {submitting ? (
                    "Signing in…"
                  ) : (
                    <>
                      Sign in as{" "}
                      {role === "candidate" ? "Candidate" : "Interviewer"}
                      <ArrowRight aria-hidden className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
                <p className="text-center text-sm text-neutral-600">
                  Don&apos;t have an account?{" "}
                  <Link
                    className="font-semibold text-blue-700"
                    href={registerHref}
                  >
                    Create an account
                  </Link>
                </p>
              </div>
            </form>
          </div>
        </section>
      </div>

      <div className="mx-auto mt-5 hidden max-w-[1320px] grid-cols-3 gap-6 px-3 md:grid">
        <TrustItem
          icon={<BadgeCheck aria-hidden />}
          title="Verified professionals"
          text="Reviewed by RoundReady"
        />
        <TrustItem
          icon={<ShieldCheck aria-hidden />}
          title="Your data is safe"
          text="Secure and private"
        />
        <TrustItem
          icon={<HeartHandshake aria-hidden />}
          title="Built to genuinely help"
          text="Affordable. Practical. Real."
        />
      </div>
    </div>
  );
}

function RoleButton({
  active,
  icon,
  label,
  onClick,
  disabled,
}: {
  active: boolean;
  icon: ReactNode;
  label: string;
  onClick(): void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      disabled={disabled}
      className={`flex h-11 items-center justify-center gap-2 rounded-lg text-sm font-semibold transition focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none disabled:opacity-50 ${active ? "bg-white text-blue-700 shadow-sm ring-1 ring-blue-200" : "text-slate-600 hover:text-slate-950"}`}
    >
      <span className="[&>svg]:h-4 [&>svg]:w-4">{icon}</span>
      {label}
    </button>
  );
}

function AuthBenefit({
  icon,
  tone,
  title,
  text,
}: {
  icon: ReactNode;
  tone: "emerald" | "blue" | "rose";
  title: string;
  text: string;
}) {
  const tones = {
    emerald: "bg-emerald-100 text-emerald-700",
    blue: "bg-blue-100 text-blue-700",
    rose: "bg-rose-100 text-rose-600",
  };
  return (
    <div className="flex items-center gap-4">
      <span
        className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full [&>svg]:h-5 [&>svg]:w-5 ${tones[tone]}`}
      >
        {icon}
      </span>
      <div>
        <h3 className="font-semibold text-slate-950">{title}</h3>
        <p className="mt-0.5 text-sm text-slate-600">{text}</p>
      </div>
    </div>
  );
}

function TrustItem({
  icon,
  title,
  text,
}: {
  icon: ReactNode;
  title: string;
  text: string;
}) {
  return (
    <div className="flex items-center justify-center gap-3 text-slate-700">
      <span className="text-slate-800 [&>svg]:h-6 [&>svg]:w-6">{icon}</span>
      <div>
        <p className="text-sm font-semibold text-slate-900">{title}</p>
        <p className="text-xs text-slate-500">{text}</p>
      </div>
    </div>
  );
}
