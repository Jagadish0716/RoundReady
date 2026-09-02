import { describe, expect, it } from "vitest";
import { protectedRouteDecision } from "@/lib/auth/guard";
import { initialAuthState, type AuthState } from "@/lib/auth/state";

const candidate: AuthState = {
  status: "authenticated",
  session: {
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
      accessExpiresAt: "soon",
      refreshExpiresAt: "later",
    },
  },
};

describe("protectedRouteDecision", () => {
  it("requires authentication", () =>
    expect(protectedRouteDecision(initialAuthState)).toBe("unauthorized"));
  it("allows an authenticated route", () =>
    expect(protectedRouteDecision(candidate)).toBe("allow"));
  it("enforces roles", () =>
    expect(protectedRouteDecision(candidate, ["admin"])).toBe("forbidden"));
  it("allows the matching role", () =>
    expect(protectedRouteDecision(candidate, ["candidate"])).toBe("allow"));
});
