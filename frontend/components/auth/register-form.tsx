"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { authErrorMessage } from "@/components/auth/auth-error";
import { PasswordField } from "@/components/auth/password-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import * as authApi from "@/lib/auth/api";
import { validateRegistration } from "@/lib/auth/validation";
import type { RegistrationRole } from "@/types/auth";

export function RegisterForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [role, setRole] = useState<RegistrationRole>("candidate");
  const [errors, setErrors] = useState<ReturnType<typeof validateRegistration>>(
    {},
  );
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validateRegistration(email, password, confirmation);
    setErrors(validation);
    setApiError(null);
    if (Object.keys(validation).length) return;
    setSubmitting(true);
    try {
      await authApi.register(email.trim(), password, role);
      router.replace("/login?registered=1");
    } catch (error) {
      setApiError(authErrorMessage(error, "register"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="mx-auto max-w-md space-y-5" onSubmit={submit} noValidate>
      <div>
        <h1 className="text-2xl font-semibold">Create an account</h1>
        <p className="mt-1 text-sm text-neutral-600">
          Choose the account type that matches how you will use RoundReady.
        </p>
      </div>
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
      <div className="space-y-2">
        <Label htmlFor="role">Account type</Label>
        <select
          id="role"
          value={role}
          disabled={submitting}
          onChange={(event) => setRole(event.target.value as RegistrationRole)}
          className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm"
        >
          <option value="candidate">Candidate</option>
          <option value="interviewer">Interviewer</option>
        </select>
      </div>
      <PasswordField
        id="password"
        label="Password"
        value={password}
        error={errors.password}
        disabled={submitting}
        onChange={setPassword}
      />
      <PasswordField
        id="confirmation"
        label="Confirm password"
        value={confirmation}
        error={errors.confirmation}
        disabled={submitting}
        onChange={setConfirmation}
      />
      <Button className="w-full" type="submit" disabled={submitting}>
        {submitting ? "Creating account…" : "Create account"}
      </Button>
      <p className="text-center text-sm text-neutral-600">
        Already registered?{" "}
        <Link className="font-medium text-neutral-900" href="/login">
          Sign in
        </Link>
      </p>
    </form>
  );
}
