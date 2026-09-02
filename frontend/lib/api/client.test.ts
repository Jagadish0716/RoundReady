import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClientError, apiRequest } from "@/lib/api/client";

afterEach(() => vi.unstubAllGlobals());

describe("apiRequest", () => {
  it.each([
    [401, "unauthenticated"],
    [403, "forbidden"],
    [404, "not_found"],
    [409, "conflict"],
    [422, "validation"],
    [429, "rate_limited"],
    [503, "server"],
  ] as const)("maps status %i to %s", async (status, kind) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "test_error", message: "Failure", details: null },
            correlation_id: "corr-1",
          }),
          { status, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    const request = apiRequest("/v1/test");
    await expect(request).rejects.toBeInstanceOf(ApiClientError);
    await expect(request).rejects.toMatchObject({
      status,
      kind,
      code: "test_error",
      correlationId: "corr-1",
    });
  });

  it("sends bearer and correlation headers", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ ok: true })));
    vi.stubGlobal("fetch", fetchMock);
    await apiRequest("/v1/test", {
      accessToken: "access",
      correlationId: "corr",
      method: "GET",
    });
    const headers = new Headers(fetchMock.mock.calls[0]?.[1]?.headers);
    expect(headers.get("Authorization")).toBe("Bearer access");
    expect(headers.get("X-Correlation-ID")).toBe("corr");
  });
});
