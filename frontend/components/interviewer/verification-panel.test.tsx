import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { VerificationPanel } from "@/components/interviewer/verification-panel";

const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({
    request: mocks.request,
    state: {
      status: "authenticated",
      session: { user: { email: "account@example.com" } },
    },
  }),
}));

const profile = {
  full_name: "Jagadisha V",
  headline: "Cloud Architect",
  company: "Amazon",
  job_title: "DevOps Engineer",
  experience_years: "15.0",
  linkedin_url: "https://linkedin.com/in/jagadisha",
  github_url: "https://github.com/jagadisha",
  bio: "Cloud and DevOps interviewer with extensive architecture mentoring experience.",
};
const detail = {
  interviewer_id: "11111111-1111-4111-8111-111111111111",
  status: "pending",
  submitted_at: null,
  reviewed_at: null,
  rejection_reason: null,
  suspension_reason: null,
  evidence: [],
  checks: [],
  screening: null,
  history: [],
  account_email: "account@example.com",
  account_email_verified: false,
  mobile_e164: null,
  mobile_verified: false,
  company_email: null,
  company_email_verified: false,
};

describe("VerificationPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
    cleanup();
  });

  it("shows immutable account email and reuses professional URLs", async () => {
    mocks.request.mockImplementation((path: string) =>
      Promise.resolve(path.endsWith("/profile") ? profile : detail),
    );
    render(<VerificationPanel />);
    expect(await screen.findByLabelText("Account email")).toHaveValue(
      "account@example.com",
    );
    expect(screen.getByLabelText("Account email")).toBeDisabled();
    expect(screen.getAllByRole("link", { name: "View profile" })).toHaveLength(
      2,
    );
    expect(screen.queryByLabelText("LinkedIn URL")).not.toBeInTheDocument();
  });

  it("validates India mobile, requests OTP, and verifies it", async () => {
    mocks.request.mockImplementation((path: string) => {
      if (path.endsWith("/profile")) return Promise.resolve(profile);
      if (path.endsWith("/mobile/request"))
        return Promise.resolve({
          challenge_id: "challenge",
          expires_at: "2026-09-08T12:00:00Z",
          resend_available_at: "2026-09-08T11:56:00Z",
          development_secret: "123456",
        });
      if (path.endsWith("/mobile/verify"))
        return Promise.resolve({ ...detail, mobile_verified: true });
      return Promise.resolve(detail);
    });
    render(<VerificationPanel />);
    const mobile = await screen.findByLabelText("Mobile number");
    fireEvent.change(mobile, { target: { value: "1234567890" } });
    fireEvent.click(screen.getByRole("button", { name: "Send OTP" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("valid mobile");
    fireEvent.change(mobile, { target: { value: "9876543210" } });
    fireEvent.click(screen.getByRole("button", { name: "Send OTP" }));
    expect(
      await screen.findByText("Development code: 123456"),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Verification code"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));
    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        "/v1/interviewers/me/verification/mobile/verify",
        {
          method: "POST",
          body: { challenge_id: "challenge", secret: "123456" },
        },
      ),
    );
  });

  it("requests and completes development company-email verification", async () => {
    mocks.request.mockImplementation((path: string) => {
      if (path.endsWith("/profile")) return Promise.resolve(profile);
      if (path.endsWith("/company-email/request"))
        return Promise.resolve({
          challenge_id: "email-challenge",
          expires_at: "2026-09-08T12:00:00Z",
          resend_available_at: "2026-09-08T11:56:00Z",
          development_secret: "secure-token",
        });
      if (path.endsWith("/company-email/verify"))
        return Promise.resolve({ ...detail, company_email_verified: true });
      return Promise.resolve(detail);
    });
    render(<VerificationPanel />);
    fireEvent.change(await screen.findByLabelText("Company email"), {
      target: { value: "jagadisha@amazon.com" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Send verification email" }),
    );
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Complete development verification",
      }),
    );
    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        "/v1/interviewers/me/verification/company-email/verify",
        expect.anything(),
      ),
    );
  });
});
