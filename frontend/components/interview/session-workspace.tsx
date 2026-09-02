"use client";

import { useEffect, useState, type FormEvent } from "react";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiClientError } from "@/lib/api/client";
import * as api from "@/lib/api/interview";
import type {
  FeedbackReport,
  InterviewSession,
  ReadinessLevel,
  RoomAccess,
  Rubric,
} from "@/types/interview";
import type { Role } from "@/types/auth";

function messageFor(error: unknown): string {
  if (!(error instanceof ApiClientError))
    return "The request could not be completed.";
  if (error.status === 404) return "Interview session was not found.";
  if (error.status === 403)
    return "You are not allowed to manage this interview.";
  if (error.status === 409) {
    if (error.code === "join_window_closed")
      return "The interview room is not open yet.";
    if (error.code === "session_not_joinable")
      return "This interview can no longer be joined.";
    if (error.code === "session_not_completed")
      return "Feedback has already been submitted or the interview is not complete.";
    return error.message;
  }
  return error.message;
}

function minutes(session: InterviewSession): number {
  return Math.round(
    (new Date(session.scheduled_end).getTime() -
      new Date(session.scheduled_start).getTime()) /
      60000,
  );
}

export function SessionWorkspace({
  role,
}: {
  role: Extract<Role, "candidate" | "interviewer">;
}) {
  const { request } = useAuth();
  const [sessions, setSessions] = useState<InterviewSession[]>([]);
  const [selected, setSelected] = useState<InterviewSession | null>(null);
  const [rubric, setRubric] = useState<Rubric | null>(null);
  const [feedback, setFeedback] = useState<FeedbackReport | null>(null);
  const [room, setRoom] = useState<RoomAccess | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .listSessions(request)
      .then((items) => {
        if (!active) return;
        setSessions(items);
        setSelected(items[0] ?? null);
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

  useEffect(() => {
    if (!selected) return;
    let active = true;
    if (role === "interviewer") {
      api
        .getRubric(request, selected.id)
        .then((value) => {
          if (active) setRubric(value);
        })
        .catch((caught: unknown) => {
          if (active) setError(messageFor(caught));
        });
    } else if (selected.status === "feedback_submitted") {
      api
        .getFeedback(request, selected.id)
        .then((value) => {
          if (active) setFeedback(value);
        })
        .catch((caught: unknown) => {
          if (active) setError(messageFor(caught));
        });
    }
    return () => {
      active = false;
    };
  }, [request, role, selected]);

  function update(authoritative: InterviewSession) {
    setSelected(authoritative);
    setSessions((items) =>
      items.map((item) =>
        item.id === authoritative.id ? authoritative : item,
      ),
    );
  }

  async function act(name: string, operation: () => Promise<InterviewSession>) {
    if (busy) return;
    setBusy(name);
    setError(null);
    setNotice(null);
    try {
      update(await operation());
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(null);
    }
  }

  async function join() {
    if (!selected || busy) return;
    setBusy("join");
    setError(null);
    try {
      setRoom(await api.joinSession(request, selected.id));
      setNotice("Short-lived room access is ready.");
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(null);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || !rubric || busy) return;
    const data = new FormData(event.currentTarget);
    const strengths = String(data.get("strengths") ?? "")
      .split("\n")
      .map((x) => x.trim())
      .filter(Boolean);
    const improvements = String(data.get("improvements") ?? "")
      .split("\n")
      .map((x) => x.trim())
      .filter(Boolean);
    const summary = String(data.get("summary") ?? "").trim();
    const criterion_scores = rubric.criteria.map((criterion) => ({
      key: criterion.key,
      score: Number(data.get(`score-${criterion.key}`)),
    }));
    if (
      !strengths.length ||
      !improvements.length ||
      summary.length < 10 ||
      criterion_scores.some(
        (item, index) =>
          !Number.isInteger(item.score) ||
          item.score < 0 ||
          item.score > rubric.criteria[index]!.maximum_score,
      )
    ) {
      setError(
        "Complete every score, strength, improvement area, and a summary of at least 10 characters.",
      );
      return;
    }
    setBusy("feedback");
    setError(null);
    try {
      const report = await api.submitFeedback(request, selected.id, {
        criterion_scores,
        strengths,
        improvement_areas: improvements,
        summary,
        readiness_level: String(data.get("readiness_level")) as ReadinessLevel,
      });
      setFeedback(report);
      update(await api.getSession(request, selected.id));
      setNotice("Feedback submitted.");
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <p role="status">Loading interview sessions…</p>;
  return (
    <section className="space-y-5">
      <header>
        <h1 className="text-2xl font-semibold">Interview sessions</h1>
        <p className="mt-1 text-sm text-neutral-600">
          View assigned sessions, room access, and feedback.
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
          className="rounded-md bg-blue-50 p-3 text-sm text-blue-800"
        >
          {notice}
        </p>
      ) : null}
      {sessions.length === 0 ? (
        <p className="text-sm text-neutral-600">
          No assigned interview sessions.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {sessions.map((session) => (
            <Button
              key={session.id}
              type="button"
              variant={selected?.id === session.id ? "default" : "outline"}
              onClick={() => {
                setRoom(null);
                setFeedback(null);
                setRubric(null);
                setSelected(session);
              }}
            >
              {new Date(session.scheduled_start).toLocaleDateString()} ·{" "}
              {session.status.replaceAll("_", " ")}
            </Button>
          ))}
        </div>
      )}
      {selected ? (
        <article
          className="space-y-3 rounded-lg border bg-white p-5"
          aria-label="Selected interview session"
        >
          <div className="flex flex-wrap justify-between gap-3">
            <h2 className="font-semibold">Session {selected.id}</h2>
            <strong className="uppercase">
              {selected.status.replaceAll("_", " ")}
            </strong>
          </div>
          <p className="text-sm">Booking {selected.booking_id}</p>
          <p className="text-sm">
            Candidate {selected.candidate_id} · Interviewer{" "}
            {selected.interviewer_id}
          </p>
          <p className="text-sm">
            {new Date(selected.scheduled_start).toLocaleString()} –{" "}
            {new Date(selected.scheduled_end).toLocaleTimeString()} ·{" "}
            {minutes(selected)} minutes
          </p>
          {selected.status === "ready" || selected.status === "in_progress" ? (
            <Button
              type="button"
              disabled={busy !== null}
              onClick={() => void join()}
            >
              {busy === "join" ? "Requesting access…" : "Enter interview room"}
            </Button>
          ) : null}
          {room ? (
            <p className="text-sm text-green-700">
              Room access ready at {room.join_url}; token expires{" "}
              {new Date(room.expires_at).toLocaleTimeString()}. Recording is
              disabled.
            </p>
          ) : null}
          {role === "interviewer" && selected.status === "ready" ? (
            <Button
              type="button"
              disabled={busy !== null}
              onClick={() =>
                void act("start", () => api.startSession(request, selected.id))
              }
            >
              {busy === "start" ? "Starting…" : "Start interview"}
            </Button>
          ) : null}
          {role === "interviewer" && selected.status === "in_progress" ? (
            <Button
              type="button"
              disabled={busy !== null}
              onClick={() =>
                void act("complete", () =>
                  api.completeSession(request, selected.id),
                )
              }
            >
              {busy === "complete" ? "Completing…" : "Complete interview"}
            </Button>
          ) : null}
        </article>
      ) : null}
      {role === "interviewer" &&
      selected?.status === "feedback_pending" &&
      rubric ? (
        <form
          className="space-y-4 rounded-lg border bg-white p-5"
          onSubmit={submit}
        >
          <div>
            <h2 className="text-lg font-semibold">Structured feedback</h2>
            <p className="text-sm text-neutral-600">
              {rubric.domain} · {rubric.topic} · {rubric.experience_level}
            </p>
          </div>
          {rubric.criteria.map((criterion) => (
            <div key={criterion.key}>
              <Label htmlFor={`score-${criterion.key}`}>
                {criterion.label} (maximum {criterion.maximum_score})
              </Label>
              <Input
                className="mt-2"
                id={`score-${criterion.key}`}
                name={`score-${criterion.key}`}
                type="number"
                min="0"
                max={criterion.maximum_score}
                step="1"
                required
              />
            </div>
          ))}
          <div>
            <Label htmlFor="strengths">Strengths (one per line)</Label>
            <textarea
              id="strengths"
              name="strengths"
              className="mt-2 min-h-20 w-full rounded-md border p-3 text-sm"
              required
            />
          </div>
          <div>
            <Label htmlFor="improvements">
              Improvement areas (one per line)
            </Label>
            <textarea
              id="improvements"
              name="improvements"
              className="mt-2 min-h-20 w-full rounded-md border p-3 text-sm"
              required
            />
          </div>
          <div>
            <Label htmlFor="summary">Summary</Label>
            <textarea
              id="summary"
              name="summary"
              className="mt-2 min-h-24 w-full rounded-md border p-3 text-sm"
              minLength={10}
              required
            />
          </div>
          <div>
            <Label htmlFor="readiness_level">Readiness</Label>
            <select
              id="readiness_level"
              name="readiness_level"
              className="mt-2 h-10 w-full rounded-md border px-3"
            >
              <option value="not_ready">Not ready</option>
              <option value="developing">Developing</option>
              <option value="interview_ready">Interview ready</option>
              <option value="strong">Strong</option>
            </select>
          </div>
          <Button type="submit" disabled={busy !== null}>
            {busy === "feedback" ? "Submitting…" : "Submit feedback"}
          </Button>
        </form>
      ) : null}
      {feedback ? (
        <section
          className="space-y-3 rounded-lg border bg-white p-5"
          aria-label="Feedback report"
        >
          <div className="flex justify-between">
            <h2 className="text-lg font-semibold">Feedback report</h2>
            <strong>{feedback.total_score} points</strong>
          </div>
          <p>{feedback.summary}</p>
          <p className="text-sm">
            Readiness: {feedback.readiness_level.replaceAll("_", " ")}
          </p>
          <div>
            <h3 className="font-medium">Scores</h3>
            <ul className="list-inside list-disc text-sm">
              {feedback.criterion_scores.map((score) => (
                <li key={score.key}>
                  {score.key}: {score.score}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="font-medium">Strengths</h3>
            <ul className="list-inside list-disc text-sm">
              {feedback.strengths.map((value) => (
                <li key={value}>{value}</li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="font-medium">Improvement areas</h3>
            <ul className="list-inside list-disc text-sm">
              {feedback.improvement_areas.map((value) => (
                <li key={value}>{value}</li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}
    </section>
  );
}
