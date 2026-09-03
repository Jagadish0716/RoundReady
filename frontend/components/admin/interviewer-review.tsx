"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { ApiClientError } from "@/lib/api/client";
import {
  approveInterviewer,
  getVerificationQueue,
  reactivateInterviewer,
  rejectInterviewer,
  suspendInterviewer,
} from "@/lib/api/interviewer";
import type { InterviewerProfile } from "@/types/interviewer";

type Action = "approve" | "reject" | "suspend" | "reactivate";

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
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeAction, setActiveAction] = useState<Action | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const current = await getVerificationQueue(request);
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
    getVerificationQueue(request)
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

  async function perform(action: Action) {
    if (!selected || activeAction) return;
    const needsReason = action === "reject" || action === "suspend";
    if (needsReason && !reason.trim()) {
      setError("A reason is required for this action.");
      return;
    }
    if (!window.confirm(`Confirm ${action} for this interviewer?`)) return;
    setActiveAction(action);
    setError(null);
    setNotice(null);
    try {
      if (action === "approve")
        await approveInterviewer(request, selected.user_id);
      if (action === "reject")
        await rejectInterviewer(request, selected.user_id, reason.trim());
      if (action === "suspend")
        await suspendInterviewer(request, selected.user_id, reason.trim());
      if (action === "reactivate")
        await reactivateInterviewer(request, selected.user_id);
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
            Review submitted professional profiles.
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
                    setSelectedId(profile.user_id);
                    setReason("");
                    setError(null);
                  }}
                >
                  <span className="block font-medium">{profile.headline}</span>
                  <span className="text-xs text-slate-500 uppercase">
                    {profile.verification_status.replace("_", " ")}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {selected && (
            <article className="space-y-4 rounded-lg border bg-white p-5">
              <div>
                <h2 className="text-xl font-semibold">{selected.headline}</h2>
                <p className="text-sm text-slate-600">
                  Interviewer {selected.user_id}
                </p>
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
              <label className="block space-y-1 text-sm">
                <span className="font-medium">
                  Reason for rejection or suspension
                </span>
                <textarea
                  aria-label="Action reason"
                  className="min-h-24 w-full rounded-md border p-2"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  maxLength={1000}
                />
              </label>
              <div className="flex flex-wrap gap-2">
                {selected.verification_status === "under_review" && (
                  <>
                    <Button
                      disabled={activeAction !== null}
                      onClick={() => void perform("approve")}
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
                  </>
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
