import { describe, expect, it } from "vitest";
import { authReducer, initialAuthState } from "@/lib/auth/state";
import type { AuthSession } from "@/types/auth";

const session: AuthSession = {
  user: {
    id: "user",
    email: "candidate@example.com",
    role: "candidate",
    isActive: true,
    createdAt: "2026-01-01T00:00:00Z",
  },
  tokens: {
    accessToken: "access",
    refreshToken: "refresh",
    accessExpiresAt: "2026-01-01T00:15:00Z",
    refreshExpiresAt: "2026-01-08T00:00:00Z",
  },
};

describe("authReducer", () => {
  it("establishes and clears an in-memory session", () => {
    const authenticated = authReducer(initialAuthState, {
      type: "authenticated",
      session,
    });
    expect(authenticated.status).toBe("authenticated");
    expect(authReducer(authenticated, { type: "signed_out" })).toEqual(
      initialAuthState,
    );
  });
});
