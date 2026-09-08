"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import * as authApi from "@/lib/auth/api";
import { ApiClientError } from "@/lib/api/client";

export function VerifyEmail() {
  const search = useSearchParams();
  const token = search.get("token");
  const next = search.get("next");
  const [state, setState] = useState<
    "verifying" | "success" | "expired" | "invalid"
  >(token ? "verifying" : "invalid");
  useEffect(() => {
    if (!token) return;
    void authApi
      .verifyEmail(token)
      .then(() => setState("success"))
      .catch((error: unknown) => {
        setState(
          error instanceof ApiClientError &&
            error.code === "verification_token_expired"
            ? "expired"
            : "invalid",
        );
      });
  }, [token]);
  const loginHref = next ? `/login?next=${encodeURIComponent(next)}` : "/login";
  if (state === "verifying") return <p role="status">Verifying your email…</p>;
  if (state === "success")
    return (
      <section className="space-y-4 text-center">
        <h1 className="text-2xl font-semibold">Email verified successfully.</h1>
        <Link className="font-medium text-blue-700" href={loginHref}>
          Continue to login
        </Link>
      </section>
    );
  return (
    <section className="space-y-4 text-center">
      <h1 className="text-2xl font-semibold">
        {state === "expired"
          ? "Verification link expired"
          : "Invalid verification link"}
      </h1>
      <Link className="font-medium text-blue-700" href={loginHref}>
        Back to login
      </Link>
    </section>
  );
}
