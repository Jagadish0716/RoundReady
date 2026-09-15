import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PublicInterviewerProfile } from "@/components/public/public-interviewer-profile";

const mocks = vi.hoisted(() => ({
  listInterviewers: vi.fn(),
  listSlots: vi.fn(),
}));

vi.mock("@/lib/api/public-discovery", () => ({
  listPublicInterviewers: mocks.listInterviewers,
  listPublicSlots: mocks.listSlots,
}));

const interviewer = {
  interviewer_id: "11111111-1111-4111-8111-111111111111",
  full_name: "Jagadisha V",
  headline: "Backend interview coach",
  job_title: "Principal Engineer",
  experience_years: "12.0",
  bio: "Distributed systems specialist",
  skills: [
    {
      id: "skill-1",
      domain: "Backend",
      topic: "Python",
      skill_name: "Python",
      experience_years: "10.0",
    },
  ],
  interview_languages: ["English"],
  roundready_verified: true,
  contact_verified: true,
  professional_experience_reviewed: true,
  screening_passed: true,
  price_paise: 20000,
  currency: "INR" as const,
};

const slot = {
  id: "22222222-2222-4222-8222-222222222222",
  interviewer_id: interviewer.interviewer_id,
  rubric_id: "33333333-3333-4333-8333-333333333333",
  domain: "Backend",
  topic: "Python",
  experience_level: "mid",
  starts_at: "2030-01-01T10:00:00Z",
  ends_at: "2030-01-01T10:20:00Z",
  status: "available",
  hold_expires_at: null,
  roundready_verified: true,
};

describe("PublicInterviewerPage", () => {
  it("shows richer public details and available slots", async () => {
    mocks.listInterviewers.mockResolvedValue([interviewer]);
    mocks.listSlots.mockResolvedValue([slot]);

    render(
      <PublicInterviewerProfile id="11111111-1111-4111-8111-111111111111" />,
    );

    expect(
      await screen.findByRole("heading", { name: "Jagadisha V" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Distributed systems specialist"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Backend · Python")).toHaveLength(2);
    expect(screen.getByText("₹200")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Book interview" }),
    ).toHaveAttribute("href", expect.stringContaining("/login?next="));
  });
});
