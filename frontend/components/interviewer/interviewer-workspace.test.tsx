import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InterviewerWorkspace } from "@/components/interviewer/interviewer-workspace";
import { VerificationStatusCard } from "@/components/interviewer/verification-status";
import { ApiClientError } from "@/lib/api/client";
import type { VerificationStatus } from "@/types/interviewer";

const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ request: mocks.request }),
}));

const profile = {
  user_id: "c731b75e-6ca0-4c79-a590-33075d26481d",
  headline: "Platform engineering interviewer",
  company: "RoundReady Labs",
  job_title: "Staff Engineer",
  experience_years: "10.0",
  linkedin_url: "https://www.linkedin.com/in/interviewer",
  github_url: "https://github.com/interviewer",
  bio: "Backend and platform specialist",
  verification_status: "pending",
  verification_reason: null,
  rating_average: "0.00",
  rating_count: 0,
  completed_interviews: 0,
  reliability_score: "100.00",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function defaultApi(
  path: string,
  options?: { method?: string; body?: unknown },
): unknown {
  if (path.endsWith("/profile"))
    return options?.method === "PUT" ? profile : profile;
  if (path.endsWith("/skills")) return [];
  if (path.endsWith("/availability/weekly")) return [];
  if (path.endsWith("/availability/blockouts")) return [];
  return null;
}

describe("InterviewerWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.request.mockImplementation((path, options) =>
      Promise.resolve(defaultApi(path, options)),
    );
  });
  afterEach(cleanup);

  it("loads the owned profile and availability", async () => {
    render(<InterviewerWorkspace />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    expect(await screen.findByLabelText("Headline")).toHaveValue(
      profile.headline,
    );
    expect(screen.getByText("PENDING")).toBeInTheDocument();
    expect(screen.getByText("No weekly availability set.")).toBeInTheDocument();
  });

  it("handles profile-not-created", async () => {
    mocks.request.mockImplementation((path: string) =>
      path.endsWith("/profile")
        ? Promise.reject(
            new ApiClientError(
              "Missing",
              404,
              "not_found",
              "not_found",
              null,
              null,
            ),
          )
        : Promise.resolve([]),
    );
    render(<InterviewerWorkspace />);
    expect(
      await screen.findByText(/Create your professional profile/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Headline")).toHaveValue("");
  });

  it("saves a profile without an arbitrary user id", async () => {
    render(<InterviewerWorkspace />);
    fireEvent.change(await screen.findByLabelText("Headline"), {
      target: { value: "Updated headline" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    expect(
      await screen.findByText("Professional profile saved."),
    ).toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledWith(
      "/v1/interviewers/me/profile",
      expect.objectContaining({
        method: "PUT",
        body: expect.not.objectContaining({ user_id: expect.anything() }),
      }),
    );
  });

  it("preserves profile input after an API error", async () => {
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) => {
        if (path.endsWith("/profile") && options?.method === "PUT")
          return Promise.reject(
            new ApiClientError(
              "Unavailable",
              503,
              "server",
              "unavailable",
              null,
              null,
            ),
          );
        return Promise.resolve(defaultApi(path, options));
      },
    );
    render(<InterviewerWorkspace />);
    fireEvent.change(await screen.findByLabelText("Headline"), {
      target: { value: "Keep this value" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unavailable");
    expect(screen.getByLabelText("Headline")).toHaveValue("Keep this value");
  });

  it("creates and saves a weekly availability rule", async () => {
    const savedRule = {
      id: "rule-1",
      weekday: 1,
      start_time: "18:00:00",
      end_time: "20:00:00",
      timezone: "Asia/Kolkata",
    };
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) => {
        if (path.endsWith("/availability/weekly") && options?.method === "PUT")
          return Promise.resolve([savedRule]);
        return Promise.resolve(defaultApi(path, options));
      },
    );
    render(<InterviewerWorkspace />);
    await screen.findByLabelText("Headline");
    fireEvent.click(screen.getByRole("button", { name: "Add time" }));
    fireEvent.click(screen.getByRole("button", { name: "Save availability" }));
    expect(
      await screen.findByText("Weekly availability saved."),
    ).toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledWith(
      "/v1/interviewers/me/availability/weekly",
      expect.objectContaining({ method: "PUT" }),
    );
  });

  it("rejects an invalid availability range before calling the API", async () => {
    render(<InterviewerWorkspace />);
    await screen.findByLabelText("Headline");
    fireEvent.click(screen.getByRole("button", { name: "Add time" }));
    fireEvent.change(screen.getByLabelText("Start time 1"), {
      target: { value: "20:00" },
    });
    fireEvent.change(screen.getByLabelText("End time 1"), {
      target: { value: "18:00" },
    });
    const callsBefore = mocks.request.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Save availability" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "start time must be before end time",
    );
    expect(mocks.request).toHaveBeenCalledTimes(callsBefore);
  });

  it("creates a blockout and refreshes the list", async () => {
    const created = {
      id: "block-new",
      starts_at: "2026-09-10T10:00:00.000Z",
      ends_at: "2026-09-10T11:00:00.000Z",
      reason: "Personal",
      created_at: "2026-01-01T00:00:00Z",
    };
    let reads = 0;
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) => {
        if (
          path.endsWith("/availability/blockouts") &&
          options?.method === "POST"
        )
          return Promise.resolve(created);
        if (path.endsWith("/availability/blockouts") && !options?.method)
          return Promise.resolve(reads++ === 0 ? [] : [created]);
        return Promise.resolve(defaultApi(path, options));
      },
    );
    render(<InterviewerWorkspace />);
    await screen.findByLabelText("Headline");
    fireEvent.change(screen.getByLabelText("Starts"), {
      target: { value: "2026-09-10T15:30" },
    });
    fireEvent.change(screen.getByLabelText("Ends"), {
      target: { value: "2026-09-10T16:30" },
    });
    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "Personal" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add blockout" }));
    expect(await screen.findByText("Blockout added.")).toBeInTheDocument();
    expect(screen.getByText(/Personal/)).toBeInTheDocument();
  });

  it("deletes a blockout and refreshes the list", async () => {
    const blockout = {
      id: "block-1",
      starts_at: "2026-09-10T10:00:00Z",
      ends_at: "2026-09-10T11:00:00Z",
      reason: "Unavailable",
      created_at: "2026-01-01T00:00:00Z",
    };
    let blockoutReads = 0;
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) => {
        if (path.endsWith("/availability/blockouts") && !options?.method)
          return Promise.resolve(blockoutReads++ === 0 ? [blockout] : []);
        return Promise.resolve(defaultApi(path, options));
      },
    );
    render(<InterviewerWorkspace />);
    expect(await screen.findByText(/Unavailable/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(await screen.findByText("Blockout removed.")).toBeInTheDocument();
    expect(screen.getByText("No blockouts.")).toBeInTheDocument();
  });
});

describe("VerificationStatusCard", () => {
  afterEach(cleanup);
  it.each([
    ["pending", "Complete your professional profile"],
    ["under_review", "being reviewed"],
    ["verified", "is verified"],
    ["rejected", "not approved"],
    ["suspended", "currently suspended"],
  ] as const)("presents %s status", (status, description) => {
    render(
      <VerificationStatusCard
        status={status as VerificationStatus}
        reason={status === "rejected" ? "More evidence needed" : null}
      />,
    );
    expect(screen.getByText(description, { exact: false })).toBeInTheDocument();
  });
});
