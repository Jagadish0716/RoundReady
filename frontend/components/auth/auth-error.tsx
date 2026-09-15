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
  if (error.code === "account_blocked" && context === "login") {
    const category = error.details?.reason_category;
    return `Your RoundReady interviewer account has been blocked and can no longer be used.${typeof category === "string" ? ` Reason: ${category}.` : ""}`;
  }
  if (error.code === "account_disabled" && context === "login")
    return "This RoundReady interviewer account has been disabled and can no longer be used.";
  if (error.code === "email_verification_required" && context === "login")
    return "Your email has not been verified yet. Verify your email before continuing.";
  if (error.status === 422) return error.message;
  if (error.status === 429)
    return "Too many attempts. Please wait and try again.";
  return error.message;
}
