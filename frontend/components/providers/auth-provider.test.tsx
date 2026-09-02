import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "@/components/providers/auth-provider";
import * as apiClient from "@/lib/api/client";
import * as authApi from "@/lib/auth/api";

const navigation = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => navigation }));
vi.mock("@/lib/auth/api", () => ({
  login: vi.fn(),
  currentUser: vi.fn(),
  refresh: vi.fn(),
  logout: vi.fn(),
}));
vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();
  return { ...actual, apiRequest: vi.fn() };
});

const oldTokens = {
  accessToken: "old-access",
  refreshToken: "old-refresh-token-with-at-least-32-characters",
  accessExpiresAt: "soon",
  refreshExpiresAt: "later",
};
const newTokens = {
  accessToken: "new-access",
  refreshToken: "new-refresh-token-with-at-least-32-characters",
  accessExpiresAt: "later",
  refreshExpiresAt: "latest",
};
const user = {
  id: "user",
  email: "candidate@example.com",
  role: "candidate" as const,
  isActive: true,
  createdAt: "2026-01-01T00:00:00Z",
};

function Probe() {
  const auth = useAuth();
  return (
    <div>
      <output>{auth.state.status}</output>
      <button
        onClick={() => void auth.login("candidate@example.com", "Password123!")}
      >
        login
      </button>
      <button
        onClick={() =>
          void auth.request("/v1/protected").catch(() => undefined)
        }
      >
        request
      </button>
      <button onClick={() => void auth.logout()}>logout</button>
    </div>
  );
}

async function establishSession(): Promise<void> {
  vi.mocked(authApi.login).mockResolvedValue(oldTokens);
  vi.mocked(authApi.currentUser).mockResolvedValue(user);
  fireEvent.click(screen.getByText("login"));
  await screen.findByText("authenticated");
}

describe("AuthProvider", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  it("initializes a session after successful login", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await establishSession();
    expect(authApi.currentUser).toHaveBeenCalledWith("old-access");
  });

  it("rotates refresh tokens once and retries an expired authenticated request", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await establishSession();
    vi.mocked(apiClient.apiRequest)
      .mockRejectedValueOnce(
        new apiClient.ApiClientError(
          "Expired",
          401,
          "unauthenticated",
          "expired",
          null,
          null,
        ),
      )
      .mockRejectedValueOnce(
        new apiClient.ApiClientError(
          "Expired",
          401,
          "unauthenticated",
          "expired",
          null,
          null,
        ),
      )
      .mockResolvedValue({ ok: true });
    vi.mocked(authApi.refresh).mockResolvedValue(newTokens);
    fireEvent.click(screen.getByText("request"));
    fireEvent.click(screen.getByText("request"));
    await waitFor(() => expect(apiClient.apiRequest).toHaveBeenCalledTimes(4));
    expect(authApi.refresh).toHaveBeenCalledTimes(1);
    expect(vi.mocked(apiClient.apiRequest).mock.calls[2]?.[1]).toMatchObject({
      accessToken: "new-access",
    });
  });

  it("clears the session when refresh recovery fails", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await establishSession();
    vi.mocked(apiClient.apiRequest).mockRejectedValue(
      new apiClient.ApiClientError(
        "Expired",
        401,
        "unauthenticated",
        "expired",
        null,
        null,
      ),
    );
    vi.mocked(authApi.refresh).mockRejectedValue(new Error("refresh expired"));
    fireEvent.click(screen.getByText("request"));
    await screen.findByText("anonymous");
    expect(navigation.replace).toHaveBeenCalledWith("/login");
  });

  it("revokes and clears the session on logout", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await establishSession();
    vi.mocked(authApi.logout).mockResolvedValue();
    fireEvent.click(screen.getByText("logout"));
    await screen.findByText("anonymous");
    expect(authApi.logout).toHaveBeenCalledWith(
      oldTokens.accessToken,
      oldTokens.refreshToken,
    );
    expect(navigation.replace).toHaveBeenCalledWith("/login");
  });
});
