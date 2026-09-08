"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { ApiClientError } from "@/lib/api/client";
import {
  getAllInterviewers,
  getVerificationDetail,
  reviewVerification,
} from "@/lib/api/interviewer";
import { isInterviewerProfileComplete } from "@/lib/interviewer-profile";
import type {
  InterviewerProfile,
  VerificationDetail,
  VerificationReviewInput,
} from "@/types/interviewer";

type Action = VerificationReviewInput["action"];

function messageFor(error: unknown): string {
  if (error instanceof ApiClientError && error.status === 409)
    return "This verification action is no longer valid. Refresh and review the current status.";
  if (error instanceof ApiClientError) return error.message;
  return "Unable to load interviewer reviews.";
}

export function InterviewerReview() {
  const { request } = useAuth();
  const [profiles, setProfiles] = useState<InterviewerProfile[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<VerificationDetail | null>(null);
  const [reason, setReason] = useState("");
  const [professionalReviewed, setProfessionalReviewed] = useState(false);
  const [linkedinReviewed, setLinkedinReviewed] = useState(false);
  const [screeningPassed, setScreeningPassed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeAction, setActiveAction] = useState<Action | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const current = await getAllInterviewers(request);
      setProfiles(current);
      setSelectedId((value) =>
        value && current.some((profile) => profile.user_id === value)
          ? value
          : (current[0]?.user_id ?? null),
      );
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    let active = true;
    getAllInterviewers(request)
      .then((current) => {
        if (!active) return;
        setProfiles(current);
        setSelectedId(current[0]?.user_id ?? null);
      })
      .catch((caught: unknown) => {
        if (active) setError(messageFor(caught));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [request]);

  const selected =
    profiles.find((profile) => profile.user_id === selectedId) ?? null;

  useEffect(() => {
    let active = true;
    if (!selectedId) return;
    getVerificationDetail(request, selectedId)
      .then((value) => {
        if (active) setDetail(value);
      })
      .catch((caught: unknown) => {
        if (active) setError(messageFor(caught));
      });
    return () => {
      active = false;
    };
  }, [request, selectedId]);

  async function perform(action: Action) {
    if (!selected || activeAction) return;
    const needsReason =
      action === "reject" ||
      action === "suspend" ||
      action === "request_more_evidence";
    if (needsReason && !reason.trim()) {
      setError("A reason is required for this action.");
      return;
    }
    if (!window.confirm(`Confirm ${action} for this interviewer?`)) return;
    setActiveAction(action);
    setError(null);
    setNotice(null);
    try {
      const body: VerificationReviewInput = { action };
      if (needsReason) body.reason = reason.trim();
      if (action === "verify") {
        body.checks = {
          linkedin_reviewed: linkedinReviewed,
          professional_evidence_reviewed: professionalReviewed,
          screening_call_passed: screeningPassed,
        };
        body.screening = {
          screening_status: screeningPassed ? "passed" : "failed",
          reviewer_notes: reason.trim() || null,
          communication_assessment: "reviewed",
          technical_assessment: "reviewed",
          overall_result: "passed",
        };
      }
      await reviewVerification(request, selected.user_id, body);
      setNotice("Verification status updated.");
      setReason("");
      await load();
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setActiveAction(null);
    }
  }

  return (
    <section className="space-y-6" aria-labelledby="review-heading">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 id="review-heading" className="text-2xl font-semibold">
            Interviewer reviews
          </h1>
          <p className="text-sm text-slate-600">
            Review identity evidence, verification checks, and screening
            outcomes.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          disabled={loading}
          onClick={() => void load()}
        >
          Refresh
        </Button>
      </div>
      {loading && <p role="status">Loading verification queue…</p>}
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="text-sm text-green-700">
          {notice}
        </p>
      )}
      {!loading && !error && profiles.length === 0 && (
        <p className="rounded-lg border border-dashed p-4 text-sm text-slate-600">
          No interviewers currently require review.
        </p>
      )}
      {profiles.length > 0 && (
        <div className="grid gap-5 lg:grid-cols-[18rem_1fr]">
          <ul className="space-y-2" aria-label="Verification queue">
            {profiles.map((profile) => (
              <li key={profile.user_id}>
                <button
                  type="button"
                  className={`w-full rounded-lg border p-3 text-left ${selectedId === profile.user_id ? "border-blue-500 bg-blue-50" : "bg-white"}`}
                  onClick={() => {
                    setDetail(null);
                    setSelectedId(profile.user_id);
                    setReason("");
                    setProfessionalReviewed(false);
                    setLinkedinReviewed(false);
                    setScreeningPassed(false);
                    setError(null);
                  }}
                >
                  <span className="block font-medium">
                    {profile.full_name || "Name not provided"}
                  </span>
                  <span className="block text-sm text-slate-600">
                    {profile.headline}
                  </span>
                  <span className="text-xs text-slate-500 uppercase">
                    {profile.verification_status.replace("_", " ")}
                  </span>
                  {!isInterviewerProfileComplete(profile) && (
                    <span className="block text-xs font-medium text-amber-700">
                      Profile incomplete
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
          {selected && (
            <article className="space-y-4 rounded-lg border bg-white p-5">
              <div>
                <h2 className="text-xl font-semibold">
                  {selected.full_name || "Name not provided"}
                </h2>
                <p className="font-medium text-slate-700">
                  {selected.headline}
                </p>
                <p className="text-sm text-slate-600">ID: {selected.user_id}</p>
                {!isInterviewerProfileComplete(selected) && (
                  <p className="mt-1 text-sm font-medium text-amber-700">
                    Profile incomplete
                  </p>
                )}
              </div>
              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-medium">Status</dt>
                  <dd>{selected.verification_status.replace("_", " ")}</dd>
                </div>
                <div>
                  <dt className="font-medium">Experience</dt>
                  <dd>{selected.experience_years} years</dd>
                </div>
                <div>
                  <dt className="font-medium">Company</dt>
                  <dd>{selected.company ?? "Not provided"}</dd>
                </div>
                <div>
                  <dt className="font-medium">Job title</dt>
                  <dd>{selected.job_title ?? "Not provided"}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-medium">Bio</dt>
                  <dd>{selected.bio ?? "Not provided"}</dd>
                </div>
                {selected.verification_reason && (
                  <div className="sm:col-span-2">
                    <dt className="font-medium">Current reason</dt>
                    <dd>{selected.verification_reason}</dd>
                  </div>
                )}
              </dl>
              {(selected.linkedin_url || selected.github_url) && (
                <div className="flex gap-4 text-sm">
                  {selected.linkedin_url && (
                    <a className="underline" href={selected.linkedin_url}>
                      LinkedIn
                    </a>
                  )}
                  {selected.github_url && (
                    <a className="underline" href={selected.github_url}>
                      GitHub
                    </a>
                  )}
                </div>
              )}
              {detail ? (
                <div className="space-y-4 border-t pt-4 text-sm">
                  <div>
                    <h3 className="font-semibold">Contact ownership</h3>
                    <p>
                      Account email:{" "}
                      {detail.account_email_verified ? "Verified" : "Pending"}
                    </p>
                    <p>
                      Mobile:{" "}
                      {detail.mobile_verified
                        ? `Verified · ••••${detail.mobile_e164?.slice(-4) ?? ""}`
                        : "Pending"}
                    </p>
                    <p>
                      Company email:{" "}
                      {detail.company_email_verified ? "Verified" : "Pending"}
                    </p>
                  </div>
                  <div>
                    <h3 className="font-semibold">Evidence checklist</h3>
                    {detail.evidence.length ? (
                      <ul className="mt-2 space-y-2">
                        {detail.evidence.map((item) => (
                          <li key={item.id} className="rounded border p-2">
                            <span className="font-medium">
                              {item.evidence_type.replaceAll("_", " ")}
                            </span>
                            <span className="ml-2 text-slate-500 uppercase">
                              {item.status}
                            </span>
                            <p className="break-all text-slate-600">
                              {item.value_reference}
                            </p>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-slate-500">No evidence submitted.</p>
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold">Checks and screening</h3>
                    <ul className="mt-1">
                      {detail.checks.map((check) => (
                        <li key={check.check_type}>
                          {check.check_type.replaceAll("_", " ")}:{" "}
                          {check.passed ? "passed" : "not passed"}
                        </li>
                      ))}
                    </ul>
                    <p>
                      Screening:{" "}
                      {detail.screening?.screening_status ?? "not scheduled"}
                    </p>
                  </div>
                  <div>
                    <h3 className="font-semibold">Review history</h3>
                    {detail.history.length ? (
                      <ul className="mt-1 space-y-1">
                        {detail.history.map((item, index) => (
                          <li key={`${item.created_at}-${index}`}>
                            {item.action.replaceAll("_", " ")} by{" "}
                            {item.reviewed_by} on{" "}
                            {new Date(item.created_at).toLocaleString()}
                            {item.notes ? ` — ${item.notes}` : ""}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-slate-500">
                        No previous review actions.
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <p role="status">Loading verification details…</p>
              )}
              <label className="block space-y-1 text-sm">
                <span className="font-medium">Reviewer notes / reason</span>
                <textarea
                  aria-label="Action reason"
                  className="min-h-24 w-full rounded-md border p-2"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  maxLength={1000}
                />
              </label>
              {selected.verification_status === "under_review" && (
                <fieldset className="space-y-2 rounded border p-3 text-sm">
                  <legend className="px-1 font-medium">
                    Required approval attestations
                  </legend>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={linkedinReviewed}
                      onChange={(event) =>
                        setLinkedinReviewed(event.target.checked)
                      }
                    />
                    I reviewed the LinkedIn profile
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={professionalReviewed}
                      onChange={(event) =>
                        setProfessionalReviewed(event.target.checked)
                      }
                    />
                    I reviewed the professional evidence
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={screeningPassed}
                      onChange={(event) =>
                        setScreeningPassed(event.target.checked)
                      }
                    />
                    The interviewer passed the screening call
                  </label>
                </fieldset>
              )}
              <div className="flex flex-wrap gap-2">
                {selected.verification_status === "under_review" && (
                  <>
                    <Button
                      disabled={
                        activeAction !== null ||
                        !professionalReviewed ||
                        !linkedinReviewed ||
                        !screeningPassed
                      }
                      onClick={() => void perform("verify")}
                    >
                      Approve
                    </Button>
                    <Button
                      variant="outline"
                      disabled={activeAction !== null}
                      onClick={() => void perform("reject")}
                    >
                      Reject
                    </Button>
                    <Button
                      variant="outline"
                      disabled={activeAction !== null}
                      onClick={() => void perform("request_more_evidence")}
                    >
                      Request more evidence
                    </Button>
                  </>
                )}
                {(selected.verification_status === "pending" ||
                  selected.verification_status === "rejected") && (
                  <Button
                    disabled={activeAction !== null}
                    onClick={() => void perform("under_review")}
                  >
                    Mark under review
                  </Button>
                )}
                {selected.verification_status === "verified" && (
                  <Button
                    variant="outline"
                    disabled={activeAction !== null}
                    onClick={() => void perform("suspend")}
                  >
                    Suspend
                  </Button>
                )}
                {selected.verification_status === "suspended" && (
                  <Button
                    disabled={activeAction !== null}
                    onClick={() => void perform("reactivate")}
                  >
                    Reactivate
                  </Button>
                )}
              </div>
            </article>
          )}
        </div>
      )}
    </section>
  );
}
