"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  useRef,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

import * as authApi from "@/lib/auth/api";
import {
  apiRequest,
  ApiClientError,
  type ApiRequestOptions,
} from "@/lib/api/client";
import {
  authReducer,
  initialAuthState,
  type AuthState,
} from "@/lib/auth/state";
import type { AuthSession, AuthUser } from "@/types/auth";

interface AuthContextValue {
  state: AuthState;
  login(email: string, password: string): Promise<AuthUser>;
  refresh(): Promise<void>;
  logout(): Promise<void>;
  request<T>(path: string, options?: ApiRequestOptions): Promise<T>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialAuthState);
  const stateRef = useRef<AuthState>(initialAuthState);
  const refreshRef = useRef<Promise<AuthSession> | null>(null);
  const router = useRouter();

  const update = useCallback(
    (action: Parameters<typeof authReducer>[1]): void => {
      stateRef.current = authReducer(stateRef.current, action);
      dispatch(action);
    },
    [],
  );

  const recoverSession = useCallback(async (): Promise<AuthSession> => {
    if (refreshRef.current) return refreshRef.current;
    const current = stateRef.current;
    if (current.status !== "authenticated")
      throw new Error("No active session");
    refreshRef.current = authApi
      .refresh(current.session.tokens.refreshToken)
      .then((tokens) => {
        const session = { user: current.session.user, tokens };
        update({ type: "authenticated", session });
        return session;
      })
      .catch((error: unknown) => {
        update({ type: "signed_out" });
        router.replace("/login");
        throw error;
      })
      .finally(() => {
        refreshRef.current = null;
      });
    return refreshRef.current;
  }, [router, update]);

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      async login(email, password) {
        update({ type: "login_started" });
        try {
          const tokens = await authApi.login(email, password);
          const user = await authApi.currentUser(tokens.accessToken);
          update({ type: "authenticated", session: { user, tokens } });
          return user;
        } catch (error) {
          update({ type: "signed_out" });
          throw error;
        }
      },
      async refresh() {
        await recoverSession();
      },
      async logout() {
        const current = stateRef.current;
        if (current.status !== "authenticated") {
          router.replace("/login");
          return;
        }
        let failure: unknown;
        try {
          await authApi.logout(
            current.session.tokens.accessToken,
            current.session.tokens.refreshToken,
          );
        } catch (error) {
          failure = error;
        } finally {
          update({ type: "signed_out" });
          router.replace("/login");
        }
        if (failure) throw failure;
      },
      async request<T>(path: string, options: ApiRequestOptions = {}) {
        const current = stateRef.current;
        if (current.status !== "authenticated")
          throw new Error("No active session");
        try {
          return await apiRequest<T>(path, {
            ...options,
            accessToken: current.session.tokens.accessToken,
          });
        } catch (error) {
          if (!(error instanceof ApiClientError) || error.status !== 401)
            throw error;
          const recovered = await recoverSession();
          return apiRequest<T>(path, {
            ...options,
            accessToken: recovered.tokens.accessToken,
          });
        }
      },
    }),
    [recoverSession, router, state, update],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
