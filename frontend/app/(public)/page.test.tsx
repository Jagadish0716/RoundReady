import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HomePage from "@/app/(public)/page";

vi.mock("@/components/public/public-discovery", () => ({
  PublicDiscovery: () => <section id="interviewers">Discovery</section>,
}));

describe("HomePage", () => {
  it("presents discovery, pricing transparency, and the founder story", () => {
    render(<HomePage />);

    expect(
      screen.getAllByRole("link", { name: "Browse interviewers" })[0],
    ).toHaveAttribute("href", "#interviewers");
    expect(
      screen.getAllByRole("link", { name: "Become an interviewer" })[0],
    ).toHaveAttribute("href", "/register?role=interviewer");
    expect(
      screen.getByText("Practice interviews with real tech professionals."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Explore freely. Sign in when you're ready to book."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("One interview. ₹200.")).toHaveLength(2);
    expect(screen.getAllByText("₹150")).toHaveLength(2);
    expect(screen.getAllByText("₹50")).toHaveLength(2);
    expect(
      screen.getByRole("heading", { name: "Why I built RoundReady" }),
    ).toBeInTheDocument();
    expect(
      screen.getByAltText("Jagadish, founder of RoundReady"),
    ).toHaveAttribute(
      "src",
      expect.stringContaining("%2Fimages%2Ffounder%2Fjagadish.jpg"),
    );
    expect(document.querySelector("#interviewers")).toBeInTheDocument();
  });
});
