import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PublicDiscovery } from "@/components/public/public-discovery";

vi.mock("@/lib/api/public-discovery", () => ({
  listPublicInterviewers: () =>
    Promise.resolve([
      {
        interviewer_id: "11111111-1111-4111-8111-111111111111",
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
        currency: "INR",
      },
    ]),
  listPublicSlots: () =>
    Promise.resolve([
      {
        id: "22222222-2222-4222-8222-222222222222",
        interviewer_id: "11111111-1111-4111-8111-111111111111",
        rubric_id: "33333333-3333-4333-8333-333333333333",
        domain: "Backend",
        topic: "Python",
        experience_level: "mid",
        starts_at: "2030-01-01T10:00:00Z",
        ends_at: "2030-01-01T10:20:00Z",
        status: "available",
        hold_expires_at: null,
        roundready_verified: true,
      },
    ]),
}));

describe("PublicDiscovery", () => {
  afterEach(cleanup);
  it("shows verified interviewer details, availability, price, and a login-gated booking link", async () => {
    render(<PublicDiscovery />);
    expect(
      await screen.findByText("Backend interview coach"),
    ).toBeInTheDocument();
    expect(screen.getByText("RoundReady Verified")).toBeInTheDocument();
    expect(screen.getByText("₹200")).toBeInTheDocument();
    expect(screen.getByText("Interview language: English")).toBeInTheDocument();
    expect(
      screen.getByText("Backend · Python", { selector: "p" }),
    ).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Book interview" });
    expect(link).toHaveAttribute(
      "href",
      expect.stringContaining("/login?next="),
    );
    expect(decodeURIComponent(link.getAttribute("href") ?? "")).toContain(
      "slot=22222222-2222-4222-8222-222222222222",
    );
  });
});
