import { ApiClientError } from "@/lib/api/client";

export function authErrorMessage(
  error: unknown,
  context: "login" | "register",
): string {
  if (!(error instanceof ApiClientError))
    return "Unable to reach RoundReady. Please try again.";
  if (error.status === 409 && context === "register") {
    return "An account with this email already exists.";
  }
  if (error.status === 401 && context === "login")
    return "Email or password is incorrect.";
  if (error.status === 422) return error.message;
  if (error.status === 429)
    return "Too many attempts. Please wait and try again.";
  return error.message;
}
