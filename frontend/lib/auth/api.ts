import { apiRequest } from "@/lib/api/client";
import type { AuthUser, RegistrationRole, TokenPair } from "@/types/auth";

interface BackendIdentity {
  id: string;
  email: string;
  role: AuthUser["role"];
  is_active: boolean;
  created_at: string;
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
): Promise<AuthUser> {
  return mapIdentity(
    await apiRequest<BackendIdentity>("/v1/auth/register", {
      method: "POST",
      body: { email, password, role },
    }),
  );
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
