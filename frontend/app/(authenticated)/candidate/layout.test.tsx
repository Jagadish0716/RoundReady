import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CandidateLayout from "@/app/(authenticated)/candidate/layout";

const mocks = vi.hoisted(() => ({ pathname: "/candidate" }));
vi.mock("next/navigation", () => ({
  usePathname: () => mocks.pathname,
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({
    logout: vi.fn(),
    state: {
      status: "authenticated",
      session: {
        user: { email: "candidate@example.com", role: "candidate" },
      },
    },
  }),
}));

describe("CandidateLayout", () => {
  afterEach(cleanup);

  it.each([
    ["/candidate", "Dashboard"],
    ["/candidate/profile", "My Profile"],
    ["/candidate/interviews", "Browse Interviewers"],
    ["/candidate/bookings", "My Bookings"],
    ["/candidate/notifications", "Notifications"],
  ])("keeps the candidate shell and activates %s", (pathname, label) => {
    mocks.pathname = pathname;
    render(
      <CandidateLayout>
        <p>Section content</p>
      </CandidateLayout>,
    );
    const navigation = screen.getByLabelText("Candidate navigation");
    expect(navigation).toBeInTheDocument();
    expect(
      within(navigation).getByRole("link", { name: label }),
    ).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Section content")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Login" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Register" }),
    ).not.toBeInTheDocument();
  });
});
