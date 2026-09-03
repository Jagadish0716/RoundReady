import { describe, expect, it } from "vitest";

import { PUBLIC_ENV_KEYS, validatePublicConfig } from "@/lib/config";

describe("public frontend configuration", () => {
  it("loads development defaults", () => {
    expect(validatePublicConfig({ nodeEnvironment: "development" })).toEqual({
      environment: "development",
      apiBaseUrl: "http://127.0.0.1:8000",
      developmentPaymentsEnabled: false,
    });
  });

  it("loads an explicit production gateway", () => {
    expect(
      validatePublicConfig({
        nodeEnvironment: "production",
        apiBaseUrl: "https://api.roundready.example/",
        enableDevelopmentPayments: "false",
      }),
    ).toEqual({
      environment: "production",
      apiBaseUrl: "https://api.roundready.example",
      developmentPaymentsEnabled: false,
    });
  });

  it.each([undefined, "not-a-url", "http://localhost:8000"])(
    "rejects missing or unsafe production gateway %s",
    (apiBaseUrl) => {
      expect(() =>
        validatePublicConfig({ nodeEnvironment: "production", apiBaseUrl }),
      ).toThrow();
    },
  );

  it("enables development payments only when explicitly allowed", () => {
    expect(
      validatePublicConfig({
        nodeEnvironment: "test",
        enableDevelopmentPayments: "true",
      }).developmentPaymentsEnabled,
    ).toBe(true);
    expect(
      validatePublicConfig({ nodeEnvironment: "development" })
        .developmentPaymentsEnabled,
    ).toBe(false);
  });

  it("rejects development payment enablement in production", () => {
    expect(() =>
      validatePublicConfig({
        nodeEnvironment: "production",
        apiBaseUrl: "https://api.roundready.example",
        enableDevelopmentPayments: "true",
      }),
    ).toThrow("cannot be enabled in production");
  });

  it("exports only the intended non-secret browser variables", () => {
    expect(PUBLIC_ENV_KEYS).toEqual([
      "NEXT_PUBLIC_API_BASE_URL",
      "NEXT_PUBLIC_ENABLE_DEVELOPMENT_PAYMENTS",
    ]);
    expect(PUBLIC_ENV_KEYS.join(" ")).not.toMatch(
      /SECRET|PASSWORD|TOKEN|JWT|DATABASE|REDIS|RABBIT|LIVEKIT/i,
    );
  });
});
