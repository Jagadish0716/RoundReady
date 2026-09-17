"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowRight,
  BadgeCheck,
  BriefcaseBusiness,
  HeartHandshake,
  LockKeyhole,
  Mail,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import { Logo } from "@/components/brand/logo";
import { authErrorMessage } from "@/components/auth/auth-error";
import { PasswordField } from "@/components/auth/password-field";
import { useAuth } from "@/components/providers/auth-provider";
import { HeroSlider } from "@/components/public/hero-slider";
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
    <div className="min-h-screen overflow-x-hidden bg-[radial-gradient(circle_at_top_left,#edf4ff_0,transparent_38%),linear-gradient(135deg,#fff_0%,#f7faff_100%)] px-4 py-4 text-slate-950 sm:px-6 xl:px-7">
      <div className="mx-auto grid max-w-[1500px] gap-7 xl:min-h-[min(850px,calc(100vh-7rem))] xl:grid-cols-[minmax(0,1.48fr)_minmax(430px,0.88fr)] xl:items-stretch">
        <HeroSlider showLogo className="order-2 hidden md:block xl:order-1" />

        <section className="order-1 flex min-w-0 flex-col xl:order-2">
          <div className="mb-5 flex min-h-14 items-center justify-between gap-3 px-1 sm:px-2">
            <Link
              href="/"
              aria-label="RoundReady home"
              className="rounded-md focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none xl:hidden"
            >
              <Logo
                variant="horizontal"
                priority
                className="w-[128px] sm:w-[170px]"
              />
            </Link>
            <p className="ml-auto text-xs whitespace-nowrap text-slate-600 sm:text-sm">
              New here?{" "}
              <Link className="font-semibold text-blue-700" href={registerHref}>
                Create an account
              </Link>
            </p>
          </div>

          <div className="flex flex-1 items-center xl:py-4">
            <form
              className="w-full rounded-[1.75rem] border border-slate-200/80 bg-white p-6 shadow-[0_22px_65px_-38px_rgba(15,23,42,0.34)] sm:p-10 xl:p-11"
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
                <div className="grid grid-cols-2 overflow-hidden rounded-xl bg-slate-100">
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
                  <div className="relative">
                    <Mail
                      aria-hidden
                      className="pointer-events-none absolute top-1/2 left-4 h-5 w-5 -translate-y-1/2 text-slate-400"
                    />
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      className="h-14 rounded-xl border-slate-200 pl-12 text-base focus-visible:border-blue-500 focus-visible:ring-blue-500/20"
                      value={email}
                      disabled={submitting}
                      aria-invalid={Boolean(errors.email)}
                      onChange={(event) => setEmail(event.target.value)}
                    />
                  </div>
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
                  icon={<LockKeyhole aria-hidden />}
                />
                <Button
                  className="h-14 w-full rounded-xl bg-blue-600 text-base font-semibold shadow-lg shadow-blue-600/15 hover:bg-blue-700 focus-visible:ring-blue-600"
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
                <div className="my-1 h-px bg-slate-100" />
                <p className="pt-1 text-center text-sm text-neutral-600">
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
          text="Thoroughly reviewed by RoundReady"
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
      className={`flex h-13 items-center justify-center gap-2 border-b-2 text-sm font-semibold transition focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none disabled:opacity-50 ${active ? "border-blue-600 bg-white text-blue-700 shadow-sm ring-1 ring-blue-200 ring-inset" : "border-transparent text-slate-700 hover:bg-white/60 hover:text-slate-950"}`}
    >
      <span className="[&>svg]:h-4 [&>svg]:w-4">{icon}</span>
      {label}
    </button>
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
