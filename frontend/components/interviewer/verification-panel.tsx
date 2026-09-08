"use client";

import { useEffect, useState } from "react";
import { parsePhoneNumberFromString } from "libphonenumber-js";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import * as api from "@/lib/api/interviewer";
import { isInterviewerProfileComplete } from "@/lib/interviewer-profile";
import type {
  ContactChallenge,
  InterviewerProfile,
  VerificationDetail,
} from "@/types/interviewer";

export function VerificationPanel() {
  const { request, state } = useAuth();
  const [detail, setDetail] = useState<VerificationDetail | null>(null);
  const [profile, setProfile] = useState<InterviewerProfile | null>(null);
  const [countryCode, setCountryCode] = useState("+91");
  const [mobile, setMobile] = useState("");
  const [code, setCode] = useState("");
  const [companyEmail, setCompanyEmail] = useState("");
  const [mobileChallenge, setMobileChallenge] =
    useState<ContactChallenge | null>(null);
  const [companyChallenge, setCompanyChallenge] =
    useState<ContactChallenge | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [verification, professional] = await Promise.all([
      api.getOwnVerification(request),
      api.getInterviewerProfile(request),
    ]);
    setDetail(verification);
    setProfile(professional);
    setCompanyEmail(verification.company_email ?? "");
  }

  useEffect(() => {
    let active = true;
    Promise.all([
      api.getOwnVerification(request),
      api.getInterviewerProfile(request),
    ])
      .then(([verification, professional]) => {
        if (!active) return;
        setDetail(verification);
        setProfile(professional);
        setCompanyEmail(verification.company_email ?? "");
      })
      .catch((caught: unknown) => {
        if (active)
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load verification.",
          );
      });
    return () => {
      active = false;
    };
  }, [request]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Verification request failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function sendMobile() {
    const parsed = parsePhoneNumberFromString(`${countryCode}${mobile}`);
    if (
      !parsed?.isValid() ||
      (countryCode === "+91" && !/^[6-9]\d{9}$/.test(mobile))
    ) {
      setError("Enter a valid mobile number.");
      return;
    }
    await run(async () => {
      setMobileChallenge(
        await api.requestMobileVerification(request, parsed.number),
      );
      await load();
    });
  }

  async function verifyMobile() {
    if (!mobileChallenge || !/^\d{6}$/.test(code)) {
      setError("Enter the 6-digit verification code.");
      return;
    }
    await run(async () => {
      setDetail(
        await api.verifyMobile(request, mobileChallenge.challenge_id, code),
      );
      setMobileChallenge(null);
      setCode("");
    });
  }

  async function sendCompanyEmail() {
    if (!/^\S+@\S+\.\S+$/.test(companyEmail)) {
      setError("Enter a valid company email address.");
      return;
    }
    await run(async () => {
      setCompanyChallenge(
        await api.requestCompanyEmailVerification(request, companyEmail.trim()),
      );
      await load();
    });
  }

  if (!detail) return error ? <p role="alert">{error}</p> : null;
  const accountEmail =
    detail.account_email ??
    (state?.status === "authenticated" ? state.session.user.email : "");
  const canSubmit =
    isInterviewerProfileComplete(profile) &&
    Boolean(
      detail.account_email_verified &&
      detail.mobile_verified &&
      detail.company_email_verified,
    );

  return (
    <section
      className="space-y-6 rounded-lg border bg-white p-5"
      aria-labelledby="verification-heading"
    >
      <div>
        <h2 id="verification-heading" className="text-lg font-semibold">
          Contact verification
        </h2>
        <p className="text-sm text-slate-600">
          Status:{" "}
          <span className="font-medium uppercase">
            {detail.status.replace("_", " ")}
          </span>
        </p>
      </div>
      <div className="grid gap-5 rounded-xl bg-slate-50 p-4 sm:grid-cols-2">
        <div>
          <Label htmlFor="account-email">Account email</Label>
          <Input
            id="account-email"
            className="mt-2"
            value={accountEmail}
            readOnly
            disabled
          />
          <p className="mt-1 text-xs text-slate-500">
            This email is associated with your RoundReady account.
          </p>
          <p className="mt-1 text-sm font-medium">
            {detail.account_email_verified
              ? "Verified"
              : "Verification required"}
          </p>
        </div>
        <div>
          <Label htmlFor="company-email">Company email</Label>
          <Input
            id="company-email"
            className="mt-2"
            type="email"
            value={companyEmail}
            disabled={busy}
            onChange={(event) => setCompanyEmail(event.target.value)}
          />
          <p className="mt-1 text-xs text-slate-500">
            Use your current work email to help us verify your professional
            experience.
          </p>
          <p className="mt-1 text-sm font-medium">
            {detail.company_email_verified ? "Verified" : "Not verified"}
          </p>
          <Button
            className="mt-2"
            type="button"
            variant="outline"
            disabled={busy}
            onClick={() => void sendCompanyEmail()}
          >
            Send verification email
          </Button>
          {companyChallenge?.development_secret && (
            <Button
              className="mt-2 ml-2"
              type="button"
              variant="outline"
              onClick={() =>
                void run(async () => {
                  setDetail(
                    await api.verifyCompanyEmail(
                      request,
                      companyChallenge.challenge_id,
                      companyChallenge.development_secret!,
                    ),
                  );
                  setCompanyChallenge(null);
                })
              }
            >
              Complete development verification
            </Button>
          )}
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor="mobile-number">Mobile number</Label>
          <div className="mt-2 flex gap-2">
            <select
              aria-label="Country code"
              className="rounded-md border px-3"
              value={countryCode}
              onChange={(event) => setCountryCode(event.target.value)}
            >
              <option value="+91">India (+91)</option>
              <option value="+1">United States (+1)</option>
              <option value="+44">United Kingdom (+44)</option>
            </select>
            <Input
              id="mobile-number"
              inputMode="numeric"
              value={mobile}
              disabled={busy}
              onChange={(event) => {
                if (/^\d{0,15}$/.test(event.target.value))
                  setMobile(event.target.value);
              }}
            />
            <Button
              type="button"
              variant="outline"
              disabled={busy}
              onClick={() => void sendMobile()}
            >
              Send OTP
            </Button>
          </div>
          <p className="mt-1 text-sm font-medium">
            {detail.mobile_verified ? "Verified" : "Not verified"}
          </p>
          {mobileChallenge && (
            <div className="mt-3 flex gap-2">
              <Input
                aria-label="Verification code"
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(event) => {
                  if (/^\d{0,6}$/.test(event.target.value))
                    setCode(event.target.value);
                }}
              />
              <Button type="button" onClick={() => void verifyMobile()}>
                Verify
              </Button>
            </div>
          )}
          {mobileChallenge?.development_secret && (
            <p className="mt-1 text-xs text-slate-500">
              Development code: {mobileChallenge.development_secret}
            </p>
          )}
        </div>
      </div>
      <div className="rounded-xl border p-4">
        <h3 className="font-semibold">Professional verification</h3>
        <p className="mt-2 text-sm">
          LinkedIn:{" "}
          {profile?.linkedin_url ? (
            <a className="underline" href={profile.linkedin_url}>
              View profile
            </a>
          ) : (
            "Complete your profile"
          )}
        </p>
        <p className="mt-2 text-sm">
          GitHub:{" "}
          {profile?.github_url ? (
            <a className="underline" href={profile.github_url}>
              View profile
            </a>
          ) : (
            "Complete your profile"
          )}
        </p>
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {(detail.status === "pending" || detail.status === "rejected") && (
        <div>
          {!canSubmit && (
            <p className="mb-2 text-sm text-amber-800">
              Complete your profile and all required contact verification before
              submitting for review.
            </p>
          )}
          <Button
            type="button"
            disabled={busy || !canSubmit}
            onClick={() =>
              void run(async () => {
                await api.submitVerification(request);
                await load();
              })
            }
          >
            Submit for review
          </Button>
        </div>
      )}
    </section>
  );
}
