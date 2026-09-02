import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { initialAuthState, type AuthState } from "@/lib/auth/state";

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  state: null as AuthState | null,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
  usePathname: () => "/candidate",
}));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ state: mocks.state }),
}));

const candidate: AuthState = {
  status: "authenticated",
  session: {
    user: {
      id: "candidate",
      email: "candidate@example.com",
      role: "candidate",
      isActive: true,
      createdAt: "2026-01-01T00:00:00Z",
    },
    tokens: {
      accessToken: "access",
      refreshToken: "refresh",
      accessExpiresAt: "soon",
      refreshExpiresAt: "later",
    },
  },
};

describe("ProtectedRoute", () => {
  beforeEach(() => {
    mocks.state = initialAuthState;
    vi.clearAllMocks();
  });
  afterEach(cleanup);

  it("redirects an unauthenticated user to login with a safe return path", async () => {
    render(<ProtectedRoute>private</ProtectedRoute>);
    await waitFor(() =>
      expect(mocks.replace).toHaveBeenCalledWith("/login?next=%2Fcandidate"),
    );
  });

  it("blocks the wrong role", () => {
    mocks.state = candidate;
    render(
      <ProtectedRoute allowedRoles={["interviewer"]}>private</ProtectedRoute>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("do not have access");
  });
});
