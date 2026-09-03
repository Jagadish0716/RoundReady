import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InterviewerReview } from "@/components/admin/interviewer-review";
import { ApiClientError } from "@/lib/api/client";
import type { InterviewerProfile } from "@/types/interviewer";

const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ request: mocks.request }),
}));

const profile: InterviewerProfile = {
  user_id: "11111111-1111-4111-8111-111111111111",
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

describe("InterviewerReview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("loads and renders the review queue and profile detail", async () => {
    mocks.request.mockResolvedValue([profile]);
    render(<InterviewerReview />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    expect(
      await screen.findByRole("heading", { name: profile.headline }),
    ).toBeInTheDocument();
    expect(screen.getByText("RoundReady Labs")).toBeInTheDocument();
    expect(screen.getByText(profile.bio!)).toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledWith(
      "/v1/interviewers/admin/verification-queue",
    );
  });

  it("shows the empty state", async () => {
    mocks.request.mockResolvedValue([]);
    render(<InterviewerReview />);
    expect(
      await screen.findByText(/No interviewers currently require review/),
    ).toBeInTheDocument();
  });

  it("approves after confirmation and refreshes the queue", async () => {
    mocks.request
      .mockResolvedValueOnce([profile])
      .mockResolvedValueOnce({ ...profile, verification_status: "verified" })
      .mockResolvedValueOnce([]);
    render(<InterviewerReview />);
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    expect(
      await screen.findByText("Verification status updated."),
    ).toBeInTheDocument();
    expect(window.confirm).toHaveBeenCalled();
    expect(mocks.request).toHaveBeenNthCalledWith(
      2,
      `/v1/interviewers/admin/interviewers/${profile.user_id}/approve`,
      { method: "POST" },
    );
    expect(mocks.request).toHaveBeenCalledTimes(3);
  });

  it("requires and submits a rejection reason", async () => {
    mocks.request
      .mockResolvedValueOnce([profile])
      .mockResolvedValueOnce({ ...profile, verification_status: "rejected" })
      .mockResolvedValueOnce([]);
    render(<InterviewerReview />);
    fireEvent.click(await screen.findByRole("button", { name: "Reject" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "reason is required",
    );
    fireEvent.change(screen.getByLabelText("Action reason"), {
      target: { value: "Experience could not be verified" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    await screen.findByText("Verification status updated.");
    expect(mocks.request).toHaveBeenNthCalledWith(
      2,
      `/v1/interviewers/admin/interviewers/${profile.user_id}/reject`,
      { method: "POST", body: { reason: "Experience could not be verified" } },
    );
  });

  it("supports the existing suspend contract with a required reason", async () => {
    const verified = { ...profile, verification_status: "verified" as const };
    mocks.request
      .mockResolvedValueOnce([verified])
      .mockResolvedValueOnce({ ...verified, verification_status: "suspended" })
      .mockResolvedValueOnce([]);
    render(<InterviewerReview />);
    fireEvent.change(await screen.findByLabelText("Action reason"), {
      target: { value: "Policy review" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Suspend" }));
    await screen.findByText("Verification status updated.");
    expect(mocks.request).toHaveBeenNthCalledWith(
      2,
      `/v1/interviewers/admin/interviewers/${profile.user_id}/suspend`,
      { method: "POST", body: { reason: "Policy review" } },
    );
  });

  it("maps invalid transitions without inventing a status", async () => {
    mocks.request
      .mockResolvedValueOnce([profile])
      .mockRejectedValueOnce(
        new ApiClientError(
          "Invalid",
          409,
          "conflict",
          "invalid_transition",
          null,
          null,
        ),
      );
    render(<InterviewerReview />);
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "no longer valid",
    );
    expect(screen.getAllByText("under review").length).toBeGreaterThan(0);
  });

  it("disables duplicate actions while mutation is pending", async () => {
    mocks.request
      .mockResolvedValueOnce([profile])
      .mockReturnValueOnce(new Promise(() => undefined));
    render(<InterviewerReview />);
    const approve = await screen.findByRole("button", { name: "Approve" });
    fireEvent.click(approve);
    fireEvent.click(approve);
    await waitFor(() => expect(approve).toBeDisabled());
    expect(mocks.request).toHaveBeenCalledTimes(2);
  });

  it("shows queue API failures", async () => {
    mocks.request.mockRejectedValue(
      new ApiClientError(
        "Review service unavailable",
        503,
        "server",
        "unavailable",
        null,
        null,
      ),
    );
    render(<InterviewerReview />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Review service unavailable",
    );
  });
});
