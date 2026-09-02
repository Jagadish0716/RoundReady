import type { AuthSession } from "@/types/auth";

export type AuthState =
  | { status: "anonymous"; session: null }
  | { status: "authenticating"; session: null }
  | { status: "authenticated"; session: AuthSession };

export type AuthAction =
  | { type: "login_started" }
  | { type: "authenticated"; session: AuthSession }
  | { type: "signed_out" };

export const initialAuthState: AuthState = {
  status: "anonymous",
  session: null,
};

export function authReducer(_state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "login_started":
      return { status: "authenticating", session: null };
    case "authenticated":
      return { status: "authenticated", session: action.session };
    case "signed_out":
      return initialAuthState;
  }
}
