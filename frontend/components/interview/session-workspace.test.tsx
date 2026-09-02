import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionWorkspace } from "@/components/interview/session-workspace";
import { ApiClientError } from "@/lib/api/client";

const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ request: mocks.request }),
}));

const ready = {
  id: "session-1",
  booking_id: "booking-1",
  candidate_id: "candidate-1",
  interviewer_id: "interviewer-1",
  rubric_id: "rubric-1",
  scheduled_start: "2030-01-01T10:00:00Z",
  scheduled_end: "2030-01-01T10:20:00Z",
  actual_start: null,
  actual_end: null,
  total_duration_seconds: 0,
  status: "ready",
};
const rubric = {
  id: "rubric-1",
  domain: "Backend",
  topic: "Python APIs",
  experience_level: "mid",
  version: 1,
  maximum_score: 15,
  active: true,
  criteria: [
    { key: "design", label: "System design", weight: 60, maximum_score: 10 },
    {
      key: "communication",
      label: "Communication",
      weight: 40,
      maximum_score: 5,
    },
  ],
};
const report = {
  id: "feedback-1",
  session_id: ready.id,
  criterion_scores: [
    { key: "design", score: 8 },
    { key: "communication", score: 4 },
  ],
  strengths: ["Clear design"],
  improvement_areas: ["Failure modes"],
  summary: "Solid backend fundamentals.",
  readiness_level: "interview_ready",
  total_score: 12,
  submitted_at: "2030-01-01T11:00:00Z",
};

function api(path: string, options?: { method?: string }): unknown {
  if (path === "/v1/interviews/sessions") return [ready];
  if (path.endsWith("/rubric")) return rubric;
  if (path.endsWith("/join"))
    return {
      token: "private-token",
      expires_at: "2030-01-01T10:05:00Z",
      join_url: "ws://livekit.local",
    };
  if (path.endsWith("/start"))
    return {
      ...ready,
      status: "in_progress",
      actual_start: "2030-01-01T10:00:00Z",
    };
  if (path.endsWith("/complete"))
    return {
      ...ready,
      status: "feedback_pending",
      actual_start: "2030-01-01T10:00:00Z",
      actual_end: "2030-01-01T10:20:00Z",
    };
  if (path.endsWith("/feedback") && options?.method === "POST") return report;
  if (path.endsWith("/feedback")) return report;
  if (path.endsWith(ready.id))
    return { ...ready, status: "feedback_submitted" };
  throw new Error(`Unexpected ${path}`);
}

describe("SessionWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.request.mockImplementation((path, options) =>
      Promise.resolve(api(path, options)),
    );
  });
  afterEach(cleanup);

  it("loads and displays an assigned READY session", async () => {
    render(<SessionWorkspace role="candidate" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    expect(await screen.findByText(/^ready$/i)).toBeInTheDocument();
    expect(screen.getByText(/Booking booking-1/)).toBeInTheDocument();
    expect(screen.getByText(/20 minutes/)).toBeInTheDocument();
  });

  it("requests short-lived participant room access without rendering its token", async () => {
    render(<SessionWorkspace role="candidate" />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Enter interview room" }),
    );
    expect(await screen.findByText(/Room access ready/)).toHaveTextContent(
      "Recording is disabled",
    );
    expect(document.body).not.toHaveTextContent("private-token");
    expect(mocks.request).toHaveBeenCalledWith(
      "/v1/interviews/sessions/session-1/join",
      { method: "POST" },
    );
  });

  it("lets the interviewer start and shows authoritative IN_PROGRESS", async () => {
    render(<SessionWorkspace role="interviewer" />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Start interview" }),
    );
    expect((await screen.findAllByText(/in progress/i)).length).toBeGreaterThan(
      0,
    );
    expect(
      screen.getByRole("button", { name: "Complete interview" }),
    ).toBeInTheDocument();
  });

  it("completes an interview into FEEDBACK_PENDING", async () => {
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) => {
        if (path === "/v1/interviews/sessions")
          return Promise.resolve([{ ...ready, status: "in_progress" }]);
        return Promise.resolve(api(path, options));
      },
    );
    render(<SessionWorkspace role="interviewer" />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Complete interview" }),
    );
    expect(
      (await screen.findAllByText(/feedback pending/i)).length,
    ).toBeGreaterThan(0);
    expect(await screen.findByText("Structured feedback")).toBeInTheDocument();
  });

  it("submits valid rubric-based feedback and reaches FEEDBACK_SUBMITTED", async () => {
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) => {
        if (path === "/v1/interviews/sessions")
          return Promise.resolve([{ ...ready, status: "feedback_pending" }]);
        return Promise.resolve(api(path, options));
      },
    );
    render(<SessionWorkspace role="interviewer" />);
    fireEvent.change(await screen.findByLabelText(/System design/), {
      target: { value: "8" },
    });
    fireEvent.change(screen.getByLabelText(/Communication/), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByLabelText(/Strengths/), {
      target: { value: "Clear design" },
    });
    fireEvent.change(screen.getByLabelText(/Improvement areas/), {
      target: { value: "Failure modes" },
    });
    fireEvent.change(screen.getByLabelText("Summary"), {
      target: { value: "Solid backend fundamentals." },
    });
    fireEvent.change(screen.getByLabelText("Readiness"), {
      target: { value: "interview_ready" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));
    expect(await screen.findByText("Feedback submitted.")).toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledWith(
      "/v1/interviews/sessions/session-1/feedback",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({ readiness_level: "interview_ready" }),
      }),
    );
  });

  it("shows duplicate feedback conflict", async () => {
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) => {
        if (path === "/v1/interviews/sessions")
          return Promise.resolve([{ ...ready, status: "feedback_pending" }]);
        if (path.endsWith("/feedback") && options?.method === "POST")
          return Promise.reject(
            new ApiClientError(
              "Already submitted",
              409,
              "conflict",
              "session_not_completed",
              null,
              null,
            ),
          );
        return Promise.resolve(api(path, options));
      },
    );
    render(<SessionWorkspace role="interviewer" />);
    fireEvent.change(await screen.findByLabelText(/System design/), {
      target: { value: "8" },
    });
    fireEvent.change(screen.getByLabelText(/Communication/), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByLabelText(/Strengths/), {
      target: { value: "Clear design" },
    });
    fireEvent.change(screen.getByLabelText(/Improvement areas/), {
      target: { value: "Failure modes" },
    });
    fireEvent.change(screen.getByLabelText("Summary"), {
      target: { value: "Solid backend fundamentals." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "already been submitted",
    );
  });

  it("loads submitted feedback read-only for the candidate", async () => {
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) => {
        if (path === "/v1/interviews/sessions")
          return Promise.resolve([{ ...ready, status: "feedback_submitted" }]);
        return Promise.resolve(api(path, options));
      },
    );
    render(<SessionWorkspace role="candidate" />);
    expect(await screen.findByText("Feedback report")).toBeInTheDocument();
    expect(screen.getByText("Solid backend fundamentals.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Submit feedback" }),
    ).not.toBeInTheDocument();
  });

  it("shows room-not-ready and API errors", async () => {
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) =>
        path.endsWith("/join")
          ? Promise.reject(
              new ApiClientError(
                "Closed",
                409,
                "conflict",
                "join_window_closed",
                null,
                null,
              ),
            )
          : Promise.resolve(api(path, options)),
    );
    render(<SessionWorkspace role="candidate" />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Enter interview room" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("not open yet");
  });

  it("does not render interviewer lifecycle or feedback controls for candidates", async () => {
    render(<SessionWorkspace role="candidate" />);
    await screen.findByText(/^ready$/i);
    expect(
      screen.queryByRole("button", { name: "Start interview" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Complete interview" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Submit feedback" }),
    ).not.toBeInTheDocument();
  });
});
