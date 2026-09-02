import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CandidateProfileForm } from "@/components/candidate/candidate-profile";
import { ApiClientError } from "@/lib/api/client";

const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ request: mocks.request }),
}));

const storedProfile = {
  user_id: "6dc6fd41-0f01-49f8-943e-3480571275f2",
  full_name: "Asha Rao",
  phone: "+919876543210",
  email: "asha@example.com",
  city: "Bengaluru",
  experience_years: "4.5",
  current_role: "Software Engineer",
  target_role: "Senior Backend Engineer",
  preferred_language: "English",
  linkedin_url: "https://www.linkedin.com/in/asha",
  resume_url: "https://example.com/asha-resume.pdf",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function save(): void {
  fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
}

describe("CandidateProfileForm", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  it("loads an existing profile", async () => {
    mocks.request.mockResolvedValue(storedProfile);
    render(<CandidateProfileForm />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    expect(await screen.findByLabelText("Full name")).toHaveValue("Asha Rao");
    expect(screen.getByLabelText("City")).toHaveValue("Bengaluru");
    expect(mocks.request).toHaveBeenCalledWith("/v1/users/me/profile");
  });

  it("shows a create state when no profile exists", async () => {
    mocks.request.mockRejectedValue(
      new ApiClientError(
        "Not found",
        404,
        "not_found",
        "candidate_profile_not_found",
        null,
        null,
      ),
    );
    render(<CandidateProfileForm />);
    expect(await screen.findByText(/Create your profile/)).toBeInTheDocument();
    expect(screen.getByLabelText("Full name")).toHaveValue("");
  });

  it("creates a profile without sending a user identity", async () => {
    mocks.request
      .mockRejectedValueOnce(
        new ApiClientError(
          "Not found",
          404,
          "not_found",
          "candidate_profile_not_found",
          null,
          null,
        ),
      )
      .mockResolvedValueOnce(storedProfile);
    render(<CandidateProfileForm />);
    fireEvent.change(await screen.findByLabelText("Full name"), {
      target: { value: "Asha Rao" },
    });
    fireEvent.change(screen.getByLabelText("City"), {
      target: { value: "Bengaluru" },
    });
    save();
    expect(await screen.findByRole("status")).toHaveTextContent(
      "saved successfully",
    );
    expect(mocks.request).toHaveBeenLastCalledWith(
      "/v1/users/me/profile",
      expect.objectContaining({
        method: "PUT",
        body: expect.not.objectContaining({ user_id: expect.anything() }),
      }),
    );
  });

  it("updates and repopulates a saved profile", async () => {
    mocks.request
      .mockResolvedValueOnce(storedProfile)
      .mockResolvedValueOnce({ ...storedProfile, city: "Pune" });
    render(<CandidateProfileForm />);
    fireEvent.change(await screen.findByLabelText("City"), {
      target: { value: "Pune" },
    });
    save();
    await screen.findByText("Profile saved successfully.");
    expect(screen.getByLabelText("City")).toHaveValue("Pune");
  });

  it("keeps entered values when backend validation fails", async () => {
    mocks.request
      .mockResolvedValueOnce(storedProfile)
      .mockRejectedValueOnce(
        new ApiClientError(
          "Invalid",
          422,
          "validation",
          "validation_error",
          null,
          null,
        ),
      );
    render(<CandidateProfileForm />);
    fireEvent.change(await screen.findByLabelText("City"), {
      target: { value: "Chennai" },
    });
    save();
    expect(await screen.findByRole("alert")).toHaveTextContent("invalid");
    expect(screen.getByLabelText("City")).toHaveValue("Chennai");
  });

  it("shows API failures and supports retry", async () => {
    mocks.request
      .mockRejectedValueOnce(
        new ApiClientError(
          "Service unavailable",
          503,
          "server",
          "unavailable",
          null,
          null,
        ),
      )
      .mockResolvedValueOnce(storedProfile);
    render(<CandidateProfileForm />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Service unavailable",
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByLabelText("Full name")).toHaveValue("Asha Rao");
  });

  it("reports forbidden access without exposing a form", async () => {
    mocks.request.mockRejectedValue(
      new ApiClientError(
        "Forbidden",
        403,
        "forbidden",
        "insufficient_permissions",
        null,
        null,
      ),
    );
    render(<CandidateProfileForm />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "do not have access",
    );
    expect(
      screen.queryByRole("button", { name: "Save profile" }),
    ).not.toBeInTheDocument();
  });

  it("disables saving while a request is pending", async () => {
    let resolveSave: ((value: typeof storedProfile) => void) | undefined;
    mocks.request.mockResolvedValueOnce(storedProfile).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSave = resolve;
        }),
    );
    render(<CandidateProfileForm />);
    await screen.findByLabelText("Full name");
    save();
    expect(screen.getByRole("button", { name: "Saving…" })).toBeDisabled();
    resolveSave?.(storedProfile);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Save profile" }),
      ).toBeEnabled(),
    );
  });
});
