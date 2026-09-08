import { apiRequest } from "@/lib/api/client";
import type {
  AuthUser,
  RegistrationResult,
  RegistrationRole,
  TokenPair,
} from "@/types/auth";

interface BackendIdentity {
  id: string;
  email: string;
  role: AuthUser["role"];
  is_active: boolean;
  created_at: string;
  email_verified: boolean;
  email_verified_at: string | null;
  development_verification_url?: string | null;
}

interface BackendTokens {
  access_token: string;
  refresh_token: string;
  access_expires_at: string;
  refresh_expires_at: string;
}

const mapIdentity = (value: BackendIdentity): AuthUser => ({
  id: value.id,
  email: value.email,
  role: value.role,
  isActive: value.is_active,
  createdAt: value.created_at,
  emailVerified: value.email_verified,
  emailVerifiedAt: value.email_verified_at,
});

const mapTokens = (value: BackendTokens): TokenPair => ({
  accessToken: value.access_token,
  refreshToken: value.refresh_token,
  accessExpiresAt: value.access_expires_at,
  refreshExpiresAt: value.refresh_expires_at,
});

export async function register(
  email: string,
  password: string,
  role: RegistrationRole,
  next?: string | null,
): Promise<RegistrationResult> {
  const response = await apiRequest<BackendIdentity>("/v1/auth/register", {
    method: "POST",
    body: { email, password, role, next },
  });
  return {
    ...mapIdentity(response),
    developmentVerificationUrl: response.development_verification_url ?? null,
  };
}

export async function resendVerification(
  email: string,
  next?: string | null,
): Promise<void> {
  await apiRequest("/v1/auth/resend-verification", {
    method: "POST",
    body: { email, next },
  });
}

export async function verifyEmail(
  token: string,
): Promise<"verified" | "already_verified"> {
  const result = await apiRequest<{ status: "verified" | "already_verified" }>(
    "/v1/auth/verify-email",
    { method: "POST", body: { token } },
  );
  return result.status;
}

export async function login(
  email: string,
  password: string,
): Promise<TokenPair> {
  return mapTokens(
    await apiRequest<BackendTokens>("/v1/auth/login", {
      method: "POST",
      body: { email, password },
    }),
  );
}

export async function currentUser(accessToken: string): Promise<AuthUser> {
  return mapIdentity(
    await apiRequest<BackendIdentity>("/v1/auth/me", { accessToken }),
  );
}

export async function refresh(refreshToken: string): Promise<TokenPair> {
  return mapTokens(
    await apiRequest<BackendTokens>("/v1/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),
  );
}

export async function logout(
  accessToken: string,
  refreshToken: string,
): Promise<void> {
  await apiRequest<null>("/v1/auth/logout", {
    method: "POST",
    accessToken,
    body: { refresh_token: refreshToken },
  });
}
