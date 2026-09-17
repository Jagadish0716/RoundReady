import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/components/auth/login-form";
import { RegisterForm } from "@/components/auth/register-form";
import { ApiClientError } from "@/lib/api/client";

const mocks = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
  resendVerification: vi.fn(),
  replace: vi.fn(),
  requested: null as string | null,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
  useSearchParams: () => ({
    get: (key: string) => (key === "next" ? mocks.requested : null),
  }),
}));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ login: mocks.login }),
}));
vi.mock("@/lib/auth/api", () => ({
  register: mocks.register,
  resendVerification: mocks.resendVerification,
}));

function completeLogin(): void {
  fireEvent.change(screen.getByLabelText("Email address"), {
    target: { value: "user@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "Password123!" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign in as Candidate" }));
}

function completeRegistration(): void {
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "new@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "Password123!" },
  });
  fireEvent.change(screen.getByLabelText("Confirm password"), {
    target: { value: "Password123!" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
}

describe("authentication forms", () => {
  beforeEach(() => {
    mocks.requested = null;
    vi.clearAllMocks();
  });
  afterEach(cleanup);

  it.each([
    ["candidate", "/candidate"],
    ["interviewer", "/interviewer"],
    ["admin", "/admin"],
  ] as const)("logs in and redirects a %s", async (role, destination) => {
    mocks.login.mockResolvedValue({ role });
    render(<LoginForm />);
    completeLogin();
    await waitFor(() =>
      expect(mocks.replace).toHaveBeenCalledWith(destination),
    );
  });

  it("preserves only a role-compatible requested redirect", async () => {
    mocks.requested = "/candidate/interviews";
    mocks.login.mockResolvedValue({ role: "candidate" });
    render(<LoginForm />);
    completeLogin();
    await waitFor(() =>
      expect(mocks.replace).toHaveBeenCalledWith("/candidate/interviews"),
    );
  });

  it("updates the login context for an interviewer", async () => {
    mocks.login.mockResolvedValue({ role: "interviewer" });
    render(<LoginForm />);

    fireEvent.click(screen.getByRole("button", { name: "Interviewer" }));

    expect(
      screen.getByText("Sign in to your RoundReady interviewer account."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign in as Interviewer" }),
    ).toBeInTheDocument();
  });

  it("prevents double submission while login is running", async () => {
    let resolveLogin: ((value: { role: "candidate" }) => void) | undefined;
    mocks.login.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveLogin = resolve;
        }),
    );
    render(<LoginForm />);
    completeLogin();

    const submit = screen.getByRole("button", { name: "Signing in…" });
    expect(submit).toBeDisabled();
    fireEvent.click(submit);
    expect(mocks.login).toHaveBeenCalledTimes(1);

    resolveLogin?.({ role: "candidate" });
    await waitFor(() =>
      expect(mocks.replace).toHaveBeenCalledWith("/candidate"),
    );
  });

  it("uses the local optional image path and omits unavailable auth features", () => {
    const { container } = render(<LoginForm />);

    expect(container.innerHTML).toContain("/images/hero/slide1.jpg");
    expect(container.innerHTML).toContain("/images/hero/slide2.jpg");
    expect(container.innerHTML).toContain("/images/hero/slide3.jpg");
    expect(
      screen.queryByRole("link", { name: /forgot password/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /google/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toHaveAttribute(
      "type",
      "password",
    );
    fireEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "text");
  });

  it("returns a candidate to preserved booking context", async () => {
    mocks.requested = "/candidate?slot=slot-1&interviewer=interviewer-1";
    mocks.login.mockResolvedValue({ role: "candidate" });
    render(<LoginForm />);
    completeLogin();
    await waitFor(() =>
      expect(mocks.replace).toHaveBeenCalledWith(mocks.requested),
    );
  });

  it("rejects an external requested redirect", async () => {
    mocks.requested = "https://malicious.example/steal";
    mocks.login.mockResolvedValue({ role: "candidate" });
    render(<LoginForm />);
    completeLogin();
    await waitFor(() =>
      expect(mocks.replace).toHaveBeenCalledWith("/candidate"),
    );
  });

  it("shows invalid credentials", async () => {
    mocks.login.mockRejectedValue(
      new ApiClientError(
        "Invalid",
        401,
        "unauthenticated",
        "invalid_credentials",
        null,
        null,
      ),
    );
    render(<LoginForm />);
    completeLogin();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email or password is incorrect",
    );
  });

  it("explains an intentionally blocked interviewer account", async () => {
    mocks.login.mockRejectedValue(
      new ApiClientError(
        "Blocked",
        403,
        "forbidden",
        "account_blocked",
        { reason_category: "Misleading information" },
        null,
      ),
    );
    render(<LoginForm />);
    completeLogin();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "blocked and can no longer be used. Reason: Misleading information.",
    );
  });

  it("shows check-email after candidate registration", async () => {
    mocks.register.mockResolvedValue({
      id: "user",
      developmentVerificationUrl: null,
    });
    render(<RegisterForm />);
    completeRegistration();
    expect(await screen.findByText("Check your email")).toBeInTheDocument();
    expect(screen.getByText("Back to login")).toHaveAttribute("href", "/login");
  });

  it("preserves booking context when sending a registered user to login", async () => {
    mocks.requested = "/candidate?slot=slot-1&interviewer=interviewer-1";
    mocks.register.mockResolvedValue({
      id: "user",
      developmentVerificationUrl: null,
    });
    render(<RegisterForm />);
    completeRegistration();
    expect(await screen.findByText("Back to login")).toHaveAttribute(
      "href",
      `/login?next=${encodeURIComponent(mocks.requested!)}`,
    );
  });

  it("offers resend when verified credentials need email verification", async () => {
    mocks.login.mockRejectedValue(
      new ApiClientError(
        "Verify",
        403,
        "forbidden",
        "email_verification_required",
        null,
        null,
      ),
    );
    render(<LoginForm />);
    completeLogin();
    expect(
      await screen.findByText(/has not been verified/),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Resend verification email" }),
    );
    await waitFor(() =>
      expect(mocks.resendVerification).toHaveBeenCalledWith(
        "user@example.com",
        null,
      ),
    );
  });

  it("shows duplicate registration conflicts", async () => {
    mocks.register.mockRejectedValue(
      new ApiClientError(
        "Duplicate",
        409,
        "conflict",
        "email_exists",
        null,
        null,
      ),
    );
    render(<RegisterForm />);
    completeRegistration();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "already exists",
    );
  });
});
