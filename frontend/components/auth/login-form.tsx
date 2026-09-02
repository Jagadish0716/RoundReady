"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { authErrorMessage } from "@/components/auth/auth-error";
import { PasswordField } from "@/components/auth/password-field";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { redirectForRole } from "@/lib/auth/redirect";
import {
  validateCredentials,
  type CredentialsErrors,
} from "@/lib/auth/validation";

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const search = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<CredentialsErrors>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validateCredentials(email, password);
    setErrors(validation);
    setApiError(null);
    if (Object.keys(validation).length) return;
    setSubmitting(true);
    try {
      const user = await login(email.trim(), password);
      router.replace(redirectForRole(user.role, search.get("next")));
    } catch (error) {
      setApiError(authErrorMessage(error, "login"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="mx-auto max-w-md space-y-5" onSubmit={submit} noValidate>
      <div>
        <h1 className="text-2xl font-semibold">Sign in</h1>
        <p className="mt-1 text-sm text-neutral-600">
          Continue to your RoundReady workspace.
        </p>
      </div>
      {search.get("registered") === "1" ? (
        <p
          role="status"
          className="rounded-md bg-green-50 p-3 text-sm text-green-800"
        >
          Account created. Sign in to continue.
        </p>
      ) : null}
      {apiError ? (
        <p
          role="alert"
          className="rounded-md bg-red-50 p-3 text-sm text-red-800"
        >
          {apiError}
        </p>
      ) : null}
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          disabled={submitting}
          aria-invalid={Boolean(errors.email)}
          onChange={(event) => setEmail(event.target.value)}
        />
        {errors.email ? (
          <p className="text-sm text-red-700">{errors.email}</p>
        ) : null}
      </div>
      <PasswordField
        id="password"
        label="Password"
        value={password}
        error={errors.password}
        disabled={submitting}
        onChange={setPassword}
      />
      <Button className="w-full" type="submit" disabled={submitting}>
        {submitting ? "Signing in…" : "Sign in"}
      </Button>
      <p className="text-center text-sm text-neutral-600">
        New to RoundReady?{" "}
        <Link className="font-medium text-neutral-900" href="/register">
          Create an account
        </Link>
      </p>
    </form>
  );
}
