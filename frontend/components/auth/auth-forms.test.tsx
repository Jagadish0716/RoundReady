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
vi.mock("@/lib/auth/api", () => ({ register: mocks.register }));

function completeLogin(): void {
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "user@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "Password123!" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
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

  it("registers and sends the user to login", async () => {
    mocks.register.mockResolvedValue({ id: "user" });
    render(<RegisterForm />);
    completeRegistration();
    await waitFor(() =>
      expect(mocks.replace).toHaveBeenCalledWith("/login?registered=1"),
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
