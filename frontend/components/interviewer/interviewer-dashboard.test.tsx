import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { InterviewerDashboard } from "@/components/interviewer/interviewer-dashboard";

const profile = {
  headline: "Platform interviewer",
  company: "RoundReady",
  job_title: "Staff Engineer",
  experience_years: "10.0",
  linkedin_url: "https://linkedin.com/in/example",
  github_url: null,
  bio: "Experienced platform interviewer",
  verification_status: "under_review",
  verification_reason: null,
  rating_average: "4.50",
  rating_count: 2,
  completed_interviews: 8,
};
const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({
    request: mocks.request,
    state: {
      status: "authenticated",
      session: { user: { email: "john@example.com" } },
    },
  }),
}));

describe("InterviewerDashboard", () => {
  afterEach(cleanup);
  it("renders authoritative status and summary values", async () => {
    mocks.request.mockImplementation((path: string) =>
      Promise.resolve(
        path.endsWith("/profile")
          ? profile
          : path.endsWith("/skills")
            ? [{ id: "skill" }]
            : [{ id: "rule" }],
      ),
    );
    render(<InterviewerDashboard />);
    expect(
      screen.getByRole("heading", { name: "Welcome back, john!" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("UNDER REVIEW")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("4.50")).toBeInTheDocument();
    expect(screen.getByText("89%")).toBeInTheDocument();
  });
});
