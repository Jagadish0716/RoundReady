import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { VerifyEmail } from "@/components/auth/verify-email";
import { ApiClientError } from "@/lib/api/client";

const mocks = vi.hoisted(() => ({
  verifyEmail: vi.fn(),
  token: "token",
  next: "/candidate?slot=1",
}));
vi.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: (key: string) =>
      key === "token" ? mocks.token : key === "next" ? mocks.next : null,
  }),
}));
vi.mock("@/lib/auth/api", () => ({ verifyEmail: mocks.verifyEmail }));

beforeEach(() => vi.clearAllMocks());

it("verifies email and preserves booking intent to login", async () => {
  mocks.verifyEmail.mockResolvedValue("verified");
  render(<VerifyEmail />);
  expect(
    await screen.findByText("Email verified successfully."),
  ).toBeInTheDocument();
  expect(screen.getByText("Continue to login")).toHaveAttribute(
    "href",
    "/login?next=%2Fcandidate%3Fslot%3D1",
  );
});

it("renders an expired verification state", async () => {
  mocks.verifyEmail.mockRejectedValue(
    new ApiClientError(
      "Expired",
      400,
      "unexpected",
      "verification_token_expired",
      null,
      null,
    ),
  );
  render(<VerifyEmail />);
  await waitFor(() =>
    expect(screen.getByText("Verification link expired")).toBeInTheDocument(),
  );
});
