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
      screen.getByRole("heading", {
        name: "Better interview preparation. A brighter you.",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "₹200 per mock interview" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("₹150")).toHaveLength(1);
    expect(screen.getAllByText("₹50")).toHaveLength(1);
    expect(
      screen.getByRole("region", {
        name: "Why candidates choose RoundReady",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "How RoundReady works" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Why I built RoundReady" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Jagadish")).toBeInTheDocument();
    expect(screen.getAllByText("Founder, RoundReady")).toHaveLength(2);
    expect(document.querySelector("#interviewers")).toBeInTheDocument();
    expect(document.querySelector("#how-it-works")).toBeInTheDocument();
    expect(document.querySelector("#why-roundready")).toBeInTheDocument();
  });
});
