import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HomePage from "@/app/(public)/page";

vi.mock("@/components/public/public-discovery", () => ({
  PublicDiscovery: () => <section id="interviewers">Discovery</section>,
}));

describe("HomePage", () => {
  it("links both anonymous discovery actions to the discovery section", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("link", { name: "Browse interviewers" }),
    ).toHaveAttribute("href", "#interviewers");
    expect(
      screen.getByRole("link", { name: "Find an interview" }),
    ).toHaveAttribute("href", "#interviewers");
    expect(document.querySelector("#interviewers")).toBeInTheDocument();
  });
});
