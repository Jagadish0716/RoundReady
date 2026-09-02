import { ApiClientError } from "@/lib/api/client";

export function ApiErrorState({ error }: { error: unknown }) {
  const message =
    error instanceof ApiClientError ? error.message : "Something went wrong.";
  return <p role="alert">{message}</p>;
}
