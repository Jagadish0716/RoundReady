import { apiBaseUrl } from "@/lib/config";
import type { ApiErrorBody, ApiErrorKind } from "@/types/api";

const statusKinds: Partial<Record<number, ApiErrorKind>> = {
  401: "unauthenticated",
  403: "forbidden",
  404: "not_found",
  409: "conflict",
  422: "validation",
  429: "rate_limited",
};

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly kind: ApiErrorKind,
    readonly code: string,
    readonly details: Record<string, unknown> | null,
    readonly correlationId: string | null,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

export interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  accessToken?: string;
  body?: unknown;
  correlationId?: string;
}

function errorKind(status: number): ApiErrorKind {
  return statusKinds[status] ?? (status >= 500 ? "server" : "unexpected");
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (!value || typeof value !== "object" || !("error" in value)) return false;
  const error = value.error;
  return Boolean(
    error &&
    typeof error === "object" &&
    "code" in error &&
    typeof error.code === "string" &&
    "message" in error &&
    typeof error.message === "string",
  );
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    accessToken,
    body,
    correlationId = crypto.randomUUID(),
    headers,
    ...init
  } = options;
  const requestHeaders = new Headers(headers);
  requestHeaders.set("Accept", "application/json");
  requestHeaders.set("X-Correlation-ID", correlationId);
  if (body !== undefined)
    requestHeaders.set("Content-Type", "application/json");
  if (accessToken) requestHeaders.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: requestHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text) as unknown;
    } catch {
      data = null;
    }
  }
  if (!response.ok) {
    const standard = isApiErrorBody(data) ? data : null;
    throw new ApiClientError(
      standard?.error.message ??
        `API request failed with status ${response.status}`,
      response.status,
      errorKind(response.status),
      standard?.error.code ?? "unexpected_response",
      standard?.error.details ?? null,
      standard?.correlation_id ?? response.headers.get("X-Correlation-ID"),
    );
  }
  return data as T;
}
