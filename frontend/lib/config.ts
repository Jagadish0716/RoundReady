export type FrontendEnvironment = "development" | "test" | "production";

const DEVELOPMENT_API_URL = "http://127.0.0.1:8000";

export const PUBLIC_ENV_KEYS = [
  "NEXT_PUBLIC_API_BASE_URL",
  "NEXT_PUBLIC_ENABLE_DEVELOPMENT_PAYMENTS",
] as const;

interface PublicEnvironment {
  nodeEnvironment?: string;
  apiBaseUrl?: string;
  enableDevelopmentPayments?: string;
}

export interface PublicConfig {
  environment: FrontendEnvironment;
  apiBaseUrl: string;
  developmentPaymentsEnabled: boolean;
}

function currentEnvironment(): PublicEnvironment {
  return {
    nodeEnvironment: process.env.NODE_ENV,
    apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL,
    enableDevelopmentPayments:
      process.env.NEXT_PUBLIC_ENABLE_DEVELOPMENT_PAYMENTS,
  };
}

export function validatePublicConfig(
  source: PublicEnvironment = currentEnvironment(),
): PublicConfig {
  if (!source.nodeEnvironment) throw new Error("NODE_ENV must be configured");
  if (
    !(["development", "test", "production"] as const).includes(
      source.nodeEnvironment as FrontendEnvironment,
    )
  ) {
    throw new Error("NODE_ENV must be development, test, or production");
  }
  const environment = source.nodeEnvironment as FrontendEnvironment;
  const configuredUrl = source.apiBaseUrl?.trim();
  if (environment === "production" && !configuredUrl) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is required in production");
  }

  const value = configuredUrl || DEVELOPMENT_API_URL;
  let gatewayUrl: URL;
  try {
    gatewayUrl = new URL(value);
  } catch {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be a valid absolute URL");
  }
  if (
    !(["http:", "https:"] as const).includes(
      gatewayUrl.protocol as "http:" | "https:",
    )
  ) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must use HTTP or HTTPS");
  }
  if (gatewayUrl.username || gatewayUrl.password) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must not contain credentials");
  }
  if (
    environment === "production" &&
    (gatewayUrl.protocol !== "https:" ||
      ["localhost", "127.0.0.1", "::1"].includes(gatewayUrl.hostname))
  ) {
    throw new Error(
      "production gateway URL must use HTTPS and cannot be localhost",
    );
  }

  const paymentFlag = source.enableDevelopmentPayments;
  if (
    paymentFlag !== undefined &&
    paymentFlag !== "true" &&
    paymentFlag !== "false"
  ) {
    throw new Error(
      "NEXT_PUBLIC_ENABLE_DEVELOPMENT_PAYMENTS must be true or false",
    );
  }
  if (environment === "production" && paymentFlag === "true") {
    throw new Error(
      "development payment completion cannot be enabled in production",
    );
  }

  return {
    environment,
    apiBaseUrl: gatewayUrl.toString().replace(/\/$/, ""),
    developmentPaymentsEnabled:
      paymentFlag === "true" && environment !== "production",
  };
}

export function apiBaseUrl(): string {
  return validatePublicConfig().apiBaseUrl;
}

export function developmentPaymentsEnabled(): boolean {
  return validatePublicConfig().developmentPaymentsEnabled;
}
