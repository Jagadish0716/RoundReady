import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InterviewerReview } from "@/components/admin/interviewer-review";
import type {
  InterviewerProfile,
  VerificationDetail,
} from "@/types/interviewer";

const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ request: mocks.request }),
}));

const profile: InterviewerProfile = {
  user_id: "11111111-1111-4111-8111-111111111111",
  full_name: "Jagadisha V",
  headline: "Senior Backend Engineer",
  company: "RoundReady Labs",
  job_title: "Staff Engineer",
  experience_years: "9.0",
  linkedin_url: "https://linkedin.com/in/reviewer",
  github_url: "https://github.com/reviewer",
  bio: "Backend and distributed systems interviewer.",
  verification_status: "under_review",
  verification_reason: null,
  rating_average: "0.0",
  rating_count: 0,
  completed_interviews: 0,
  reliability_score: "100.0",
  created_at: "2026-09-01T10:00:00Z",
  updated_at: "2026-09-02T10:00:00Z",
};

const detail: VerificationDetail = {
  interviewer_id: profile.user_id,
  status: "under_review",
  submitted_at: "2026-09-02T10:00:00Z",
  reviewed_at: null,
  rejection_reason: null,
  suspension_reason: null,
  evidence: [
    {
      id: "22222222-2222-4222-8222-222222222222",
      evidence_type: "company_email",
      value_reference: "engineer@roundready.example",
      status: "pending",
      reviewer_notes: null,
      created_at: "2026-09-02T10:00:00Z",
      reviewed_at: null,
    },
  ],
  checks: [],
  screening: null,
  history: [],
};

describe("InterviewerReview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mocks.request.mockImplementation((path: string) => {
      if (path === "/v1/interviewers/admin/interviewers")
        return Promise.resolve([profile]);
      if (path.endsWith("/verification")) return Promise.resolve(detail);
      if (path.endsWith("/verification/review")) return Promise.resolve(detail);
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("shows profile, evidence, screening and history to admins", async () => {
    render(<InterviewerReview />);
    expect(
      await screen.findByRole("heading", { name: profile.full_name! }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: profile.user_id }),
    ).not.toBeInTheDocument();
    expect(
      await screen.findByText("engineer@roundready.example"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Screening: not scheduled/)).toBeInTheDocument();
    expect(screen.getByText(/No previous review actions/)).toBeInTheDocument();
  });

  it("approves only with professional review and a passed screening result", async () => {
    render(<InterviewerReview />);
    const approve = await screen.findByRole("button", { name: "Approve" });
    expect(approve).toBeDisabled();
    fireEvent.click(screen.getByLabelText("I reviewed the LinkedIn profile"));
    fireEvent.click(
      screen.getByLabelText("I reviewed the professional evidence"),
    );
    fireEvent.click(
      screen.getByLabelText("The interviewer passed the screening call"),
    );
    fireEvent.click(approve);
    await screen.findByText("Verification status updated.");
    expect(mocks.request).toHaveBeenCalledWith(
      `/v1/interviewers/admin/interviewers/${profile.user_id}/verification/review`,
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          action: "verify",
          checks: expect.objectContaining({
            linkedin_reviewed: true,
            professional_evidence_reviewed: true,
          }),
          screening: expect.objectContaining({ screening_status: "passed" }),
        }),
      }),
    );
  });

  it("requires a reason when requesting more evidence", async () => {
    render(<InterviewerReview />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Request more evidence" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "reason is required",
    );
    fireEvent.change(screen.getByLabelText("Action reason"), {
      target: { value: "Provide proof of company-email ownership" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Request more evidence" }),
    );
    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        `/v1/interviewers/admin/interviewers/${profile.user_id}/verification/review`,
        {
          method: "POST",
          body: {
            action: "request_more_evidence",
            reason: "Provide proof of company-email ownership",
          },
        },
      ),
    );
  });

  it("shows the empty state", async () => {
    mocks.request.mockResolvedValueOnce([]);
    render(<InterviewerReview />);
    expect(
      await screen.findByText(/No interviewers currently require review/),
    ).toBeInTheDocument();
  });
});
