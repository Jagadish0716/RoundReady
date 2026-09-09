"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { ApiClientError } from "@/lib/api/client";
import {
  approveInterviewer,
  deleteInterviewer,
  getAllInterviewers,
  getVerificationDetail,
  markLinkedinReviewed,
  recordScreening,
  reviewEvidence,
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
  if (
    error instanceof ApiClientError &&
    error.code === "verification_prerequisites_incomplete"
  ) {
    const missing = Array.isArray(error.details?.missing)
      ? error.details.missing.join(", ").replaceAll("_", " ")
      : "required verification checks";
    return `Cannot approve yet. Complete: ${missing}.`;
  }
  if (
    error instanceof ApiClientError &&
    error.code === "invalid_verification_transition"
  )
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
  const [loading, setLoading] = useState(true);
  const [activeAction, setActiveAction] = useState<Action | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [showDelete, setShowDelete] = useState(false);
  const [deleteReason, setDeleteReason] = useState("");
  const [deleting, setDeleting] = useState(false);

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
  const missingRequirements = detail?.missing_requirements ?? [];
  const hasPassed = (check: string) =>
    detail?.checks.some((item) => item.check_type === check && item.passed) ??
    false;

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
      if (action === "verify")
        await approveInterviewer(request, selected.user_id);
      else await reviewVerification(request, selected.user_id, body);
      setNotice("Verification status updated.");
      setReason("");
      await load();
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setActiveAction(null);
    }
  }

  async function professionalAction(
    action: "linkedin" | "schedule" | "pass" | "evidence",
    evidenceId?: string,
  ) {
    if (!selected || activeAction) return;
    setActiveAction("under_review");
    setError(null);
    try {
      if (action === "linkedin")
        await markLinkedinReviewed(request, selected.user_id);
      if (action === "evidence" && evidenceId)
        await reviewEvidence(
          request,
          selected.user_id,
          evidenceId,
          "verified",
          reason.trim(),
        );
      if (action === "schedule")
        await recordScreening(
          request,
          selected.user_id,
          "pending",
          reason.trim(),
        );
      if (action === "pass")
        await recordScreening(
          request,
          selected.user_id,
          "passed",
          reason.trim(),
        );
      setDetail(await getVerificationDetail(request, selected.user_id));
      setNotice("Authoritative verification state updated.");
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setActiveAction(null);
    }
  }

  async function removeInterviewer() {
    if (!selected || deleting || deleteReason.trim().length < 3) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteInterviewer(request, selected.user_id, deleteReason.trim());
      setShowDelete(false);
      setDeleteReason("");
      setNotice("Interviewer deleted from active use and public discovery.");
      await load();
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setDeleting(false);
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
              {selected.verification_status === "under_review" && detail && (
                <div className="space-y-4 rounded border p-3 text-sm">
                  <section>
                    <h3 className="font-semibold">Professional review</h3>
                    <p>
                      LinkedIn:{" "}
                      {hasPassed("linkedin_reviewed") ? "Reviewed" : "Pending"}
                    </p>
                    {!hasPassed("linkedin_reviewed") &&
                      selected.linkedin_url && (
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => void professionalAction("linkedin")}
                        >
                          Mark LinkedIn reviewed
                        </Button>
                      )}
                    <p className="mt-2">
                      Professional evidence:{" "}
                      {detail.evidence.length
                        ? hasPassed("professional_evidence_reviewed")
                          ? "Reviewed"
                          : "Pending"
                        : "No evidence submitted"}
                    </p>
                    {detail.evidence
                      .filter((item) => item.status === "pending")
                      .map((item) => (
                        <Button
                          key={item.id}
                          type="button"
                          variant="outline"
                          onClick={() =>
                            void professionalAction("evidence", item.id)
                          }
                        >
                          Accept {item.evidence_type.replaceAll("_", " ")}
                        </Button>
                      ))}
                  </section>
                  <section>
                    <h3 className="font-semibold">Screening</h3>
                    <p>
                      Status:{" "}
                      {detail.screening?.screening_status ?? "not scheduled"}
                    </p>
                    {!detail.screening && (
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => void professionalAction("schedule")}
                      >
                        Schedule screening
                      </Button>
                    )}
                    {detail.screening?.screening_status === "pending" && (
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => void professionalAction("pass")}
                      >
                        Record screening passed
                      </Button>
                    )}
                  </section>
                  <section>
                    <h3 className="font-semibold">
                      Final approval requirements
                    </h3>
                    {missingRequirements.length ? (
                      <>
                        <p className="font-medium text-amber-700">
                          Cannot approve yet
                        </p>
                        <ul>
                          {missingRequirements.map((item) => (
                            <li key={item}>❌ {item.replaceAll("_", " ")}</li>
                          ))}
                        </ul>
                      </>
                    ) : (
                      <p className="text-green-700">
                        All prerequisites complete.
                      </p>
                    )}
                  </section>
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                {selected.verification_status === "under_review" && (
                  <>
                    <Button
                      disabled={
                        activeAction !== null ||
                        !detail ||
                        missingRequirements.length > 0
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
                <Button
                  type="button"
                  variant="outline"
                  disabled={activeAction !== null || deleting}
                  onClick={() => setShowDelete(true)}
                  className="text-red-700"
                >
                  Delete interviewer
                </Button>
              </div>
              {showDelete && (
                <div
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="delete-title"
                  className="rounded-lg border border-red-200 bg-red-50 p-4"
                >
                  <h3 id="delete-title" className="font-semibold">
                    Confirm interviewer deletion
                  </h3>
                  <p className="text-sm">
                    This removes the interviewer from active use and public
                    discovery while preserving audit and interview history.
                  </p>
                  <label className="mt-3 block text-sm">
                    <span>Deletion reason</span>
                    <textarea
                      aria-label="Deletion reason"
                      className="mt-1 min-h-20 w-full rounded border bg-white p-2"
                      value={deleteReason}
                      onChange={(event) => setDeleteReason(event.target.value)}
                      maxLength={1000}
                    />
                  </label>
                  <div className="mt-3 flex gap-2">
                    <Button
                      type="button"
                      disabled={deleting || deleteReason.trim().length < 3}
                      onClick={() => void removeInterviewer()}
                    >
                      Confirm delete
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={deleting}
                      onClick={() => setShowDelete(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </article>
          )}
        </div>
      )}
    </section>
  );
}
