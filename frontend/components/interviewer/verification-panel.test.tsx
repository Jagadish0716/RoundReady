import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VerificationPanel } from "@/components/interviewer/verification-panel";
import type { VerificationDetail } from "@/types/interviewer";

const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ request: mocks.request }),
}));

const detail: VerificationDetail = {
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
};

describe("VerificationPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
    cleanup();
  });

  it("loads once, saves own evidence, and submits for review", async () => {
    mocks.request.mockImplementation((path: string) => {
      if (path === "/v1/interviewers/me/verification")
        return Promise.resolve(detail);
      if (path.endsWith("/verification/evidence"))
        return Promise.resolve(detail);
      if (path.endsWith("/verification/submit")) return Promise.resolve({});
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    render(<VerificationPanel />);
    const linkedin = await screen.findByLabelText("LinkedIn URL");
    expect(mocks.request).toHaveBeenCalledTimes(1);
    fireEvent.change(linkedin, {
      target: { value: "https://linkedin.com/in/interviewer" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);
    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        "/v1/interviewers/me/verification/evidence",
        {
          method: "PUT",
          body: {
            evidence_type: "linkedin",
            value_reference: "https://linkedin.com/in/interviewer",
          },
        },
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Submit for review" }));
    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        "/v1/interviewers/me/verification/submit",
        { method: "POST" },
      ),
    );
  });
});
