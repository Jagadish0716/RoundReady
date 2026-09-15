import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PublicDiscovery } from "@/components/public/public-discovery";

const mocks = vi.hoisted(() => ({
  listInterviewers: vi.fn(),
  listSlots: vi.fn(),
}));
vi.mock("@/lib/api/public-discovery", () => ({
  listPublicInterviewers: mocks.listInterviewers,
  listPublicSlots: mocks.listSlots,
}));

const interviewers = [
  {
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
      {
        id: "skill-2",
        domain: "Backend",
        topic: "Databases",
        skill_name: "PostgreSQL",
        experience_years: "8.0",
      },
      {
        id: "skill-3",
        domain: "Cloud",
        topic: "AWS",
        skill_name: "AWS",
        experience_years: "6.0",
      },
      {
        id: "skill-4",
        domain: "Architecture",
        topic: "Systems",
        skill_name: "System design",
        experience_years: "7.0",
      },
      {
        id: "skill-5",
        domain: "DevOps",
        topic: "Containers",
        skill_name: "Docker",
        experience_years: "5.0",
      },
      {
        id: "skill-6",
        domain: "Backend",
        topic: "APIs",
        skill_name: "FastAPI",
        experience_years: "4.0",
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
];
const slots = [
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
];

describe("PublicDiscovery", () => {
  beforeEach(() => {
    mocks.listInterviewers.mockResolvedValue(interviewers);
    mocks.listSlots.mockResolvedValue(slots);
  });
  afterEach(cleanup);
  it("shows compact comparison details and a login-gated booking link", async () => {
    render(<PublicDiscovery />);
    expect(
      await screen.findByText("Backend interview coach"),
    ).toBeInTheDocument();
    expect(screen.getByText("RoundReady Verified")).toBeInTheDocument();
    expect(screen.getByText("Jagadisha V")).toBeInTheDocument();
    expect(screen.getByText("₹200")).toBeInTheDocument();
    expect(screen.getByText("Interview language")).toBeInTheDocument();
    expect(screen.getByText("Next availability")).toBeInTheDocument();
    expect(screen.getByText("Backend")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("+1 more")).toBeInTheDocument();
    expect(
      screen.queryByText("Distributed systems specialist"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Professional experience/),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Screening/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View profile" })).toHaveAttribute(
      "href",
      "/interviewers/11111111-1111-4111-8111-111111111111",
    );
    const link = screen.getByRole("link", { name: "Book interview" });
    expect(link).toHaveAttribute(
      "href",
      expect.stringContaining("/login?next="),
    );
    expect(decodeURIComponent(link.getAttribute("href") ?? "")).toContain(
      "slot=22222222-2222-4222-8222-222222222222",
    );
  });
  it("links an authenticated candidate directly to preserved booking intent", async () => {
    render(<PublicDiscovery authenticated />);
    await screen.findByText("Backend interview coach");
    const link = screen.getByRole("link", { name: "Book interview" });
    expect(link).toHaveAttribute(
      "href",
      "/candidate?slot=22222222-2222-4222-8222-222222222222&interviewer=11111111-1111-4111-8111-111111111111",
    );
    expect(screen.queryByText(/sign in when/i)).not.toBeInTheDocument();
  });
  it("uses a neutral fallback rather than an email when a legacy name is absent", async () => {
    mocks.listInterviewers.mockResolvedValue([
      { ...interviewers[0], full_name: null },
    ]);
    render(<PublicDiscovery />);
    expect(await screen.findByText("Name not provided")).toBeInTheDocument();
    expect(screen.queryByText(/@/)).not.toBeInTheDocument();
  });
  it("shows an empty state when the APIs return no availability", async () => {
    mocks.listInterviewers.mockResolvedValue([]);
    mocks.listSlots.mockResolvedValue([]);
    render(<PublicDiscovery />);
    expect(
      await screen.findByText(
        "No interview slots are available right now. Please check again soon.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
  it("retains an error state when the availability API fails", async () => {
    mocks.listSlots.mockRejectedValue(new Error("network failure"));
    render(<PublicDiscovery />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Public interview availability could not be loaded.",
    );
  });
});
