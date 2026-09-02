export const roles = ["candidate", "interviewer", "admin"] as const;

export type Role = (typeof roles)[number];

export interface AuthUser {
  id: string;
  email: string;
  role: Role;
  isActive: boolean;
  createdAt: string;
}

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  accessExpiresAt: string;
  refreshExpiresAt: string;
}

export interface AuthSession {
  user: AuthUser;
  tokens: TokenPair;
}

export type RegistrationRole = Exclude<Role, "admin">;
