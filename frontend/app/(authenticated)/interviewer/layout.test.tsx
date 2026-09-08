import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import InterviewerLayout from "@/app/(authenticated)/interviewer/layout";

const mocks = vi.hoisted(() => ({
  pathname: "/interviewer",
  request: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  usePathname: () => mocks.pathname,
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({
    logout: vi.fn(),
    request: mocks.request,
    state: {
      status: "authenticated",
      session: {
        user: { email: "interviewer@example.com", role: "interviewer" },
      },
    },
  }),
}));

describe("InterviewerLayout", () => {
  afterEach(cleanup);
  it.each([
    ["/interviewer", "Dashboard"],
    ["/interviewer/profile", "My Profile"],
    ["/interviewer/verification", "Verification"],
    ["/interviewer/skills", "Skills & Domains"],
    ["/interviewer/availability", "Availability"],
    ["/interviewer/blockouts", "Blockouts"],
    ["/interviewer/sessions", "Interview Sessions"],
    ["/interviewer/notifications", "Notifications"],
  ])("keeps the shell and activates %s", async (pathname, label) => {
    mocks.request.mockResolvedValue({ full_name: "Jagadisha V" });
    mocks.pathname = pathname;
    render(
      <InterviewerLayout>
        <p>Section content</p>
      </InterviewerLayout>,
    );
    const navigation = screen.getByLabelText("Interviewer navigation");
    expect(
      within(navigation).getByRole("link", { name: label }),
    ).toHaveAttribute("aria-current", "page");
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Login" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Register" }),
    ).not.toBeInTheDocument();
    expect(await screen.findByText("Jagadisha V")).toBeInTheDocument();
    expect(
      screen.queryByText("interviewer@example.com"),
    ).not.toBeInTheDocument();
  });
  it("updates the sidebar name immediately after a successful profile save", async () => {
    mocks.request.mockResolvedValue({ full_name: null });
    render(
      <InterviewerLayout>
        <p>Content</p>
      </InterviewerLayout>,
    );
    expect(await screen.findByText("Name not provided")).toBeInTheDocument();
    fireEvent(
      window,
      new CustomEvent("roundready:interviewer-profile-updated", {
        detail: { fullName: "Jagadisha V" },
      }),
    );
    expect(screen.getByText("Jagadisha V")).toBeInTheDocument();
  });
});
