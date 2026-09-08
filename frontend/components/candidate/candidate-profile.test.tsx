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
  useAuth: () => ({
    request: mocks.request,
    state: {
      status: "authenticated",
      session: { user: { email: "account@example.com" } },
    },
  }),
}));
const profile = {
  user_id: "6dc6fd41-0f01-49f8-943e-3480571275f2",
  full_name: "Asha Rao",
  phone: "+919876543210",
  email: "account@example.com",
  city: "Bengaluru",
  experience_years: "4.5",
  current_role: "Software Engineer",
  target_role: "Senior Backend Engineer",
  preferred_language: "English",
  linkedin_url: "https://www.linkedin.com/in/asha",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const notFound = new ApiClientError(
  "Not found",
  404,
  "not_found",
  "not_found",
  null,
  null,
);
function defaultRequests() {
  mocks.request.mockImplementation(
    (path: string, options?: { method?: string }) => {
      if (path.endsWith("/resume")) return Promise.reject(notFound);
      if (options?.method === "PUT") return Promise.resolve(profile);
      return Promise.resolve(profile);
    },
  );
}

describe("CandidateProfileForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    defaultRequests();
  });
  afterEach(cleanup);
  it("shows a loading state while profile data is pending", () => {
    mocks.request.mockReturnValue(new Promise(() => undefined));
    render(<CandidateProfileForm />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading your profile",
    );
  });
  it("loads profile, splits phone, and shows immutable account email", async () => {
    render(<CandidateProfileForm />);
    expect(await screen.findByLabelText("Full name")).toHaveValue("Asha Rao");
    expect(screen.getByLabelText("Country code")).toHaveValue("India (+91)");
    expect(screen.getByLabelText("Mobile number")).toHaveValue("9876543210");
    expect(screen.getByLabelText("Email address")).toHaveValue(
      "account@example.com",
    );
    expect(screen.getByLabelText("Email address")).toBeDisabled();
    expect(screen.getByLabelText("Email address")).toHaveAttribute("readonly");
    expect(
      screen.getByRole("complementary", { name: "Candidate navigation" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("complementary", { name: "Profile guidance" }),
    ).toBeInTheDocument();
  });
  it("calculates profile completion from meaningful fields", async () => {
    render(<CandidateProfileForm />);
    expect(
      await screen.findByLabelText("Profile 89% complete"),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("City"), { target: { value: "" } });
    expect(screen.getByLabelText("Profile 78% complete")).toBeInTheDocument();
  });
  it("renders responsive dashboard structure without fixed page widths", async () => {
    render(<CandidateProfileForm />);
    await screen.findByLabelText("Full name");
    const dashboard = screen.getByLabelText("Candidate profile dashboard");
    expect(dashboard).toHaveClass("min-w-0");
    expect(dashboard.className).toContain("lg:grid-cols-");
    expect(dashboard.className).toContain("xl:grid-cols-");
  });
  it("submits canonical phone without email", async () => {
    render(<CandidateProfileForm />);
    await screen.findByLabelText("Full name");
    fireEvent.change(screen.getByLabelText("Mobile number"), {
      target: { value: "98765abc43210" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await screen.findByText("Profile saved successfully.");
    const save = mocks.request.mock.calls.find(
      (call) => call[1]?.method === "PUT",
    );
    expect(save?.[1].body.phone).toBe("+919876543210");
    expect(save?.[1].body).not.toHaveProperty("email");
  });
  it.each([
    "21",
    "33333333",
    "33333333.333333",
    "-1",
    "abc",
    "1e5",
    "+2",
    "1.55",
  ])(
    "rejects invalid experience input %s without displaying it",
    async (attempted) => {
      render(<CandidateProfileForm />);
      const input = await screen.findByLabelText("Experience (years)");
      expect(input).toHaveValue("4.5");
      fireEvent.change(input, { target: { value: attempted } });
      expect(input).toHaveValue("4.5");
    },
  );
  it.each(["0", "0.5", "1", "1.5", "20"])(
    "accepts and submits valid experience %s",
    async (value) => {
      render(<CandidateProfileForm />);
      const input = await screen.findByLabelText("Experience (years)");
      fireEvent.change(input, { target: { value } });
      expect(input).toHaveValue(value);
      fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
      await screen.findByText("Profile saved successfully.");
      const save = mocks.request.mock.calls.find(
        (call) => call[1]?.method === "PUT",
      );
      expect(save?.[1].body.experience_years).toBe(value);
    },
  );
  it("allows an empty value while editing and validates it on submit", async () => {
    render(<CandidateProfileForm />);
    const input = await screen.findByLabelText("Experience (years)");
    fireEvent.change(input, {
      target: { value: "" },
    });
    expect(input).toHaveValue("");
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    expect(
      await screen.findByText("Experience must be between 0 and 20 years."),
    ).toBeInTheDocument();
    expect(
      mocks.request.mock.calls.some((call) => call[1]?.method === "PUT"),
    ).toBe(false);
  });
  it("rejects pasted invalid experience content", async () => {
    render(<CandidateProfileForm />);
    const input = await screen.findByLabelText("Experience (years)");
    fireEvent.change(input, { target: { value: "999 pasted" } });
    expect(input).toHaveValue("4.5");
  });
  it("safely handles invalid historical experience returned by the API", async () => {
    mocks.request.mockImplementation((path: string) =>
      path.endsWith("/resume")
        ? Promise.reject(notFound)
        : Promise.resolve({ ...profile, experience_years: "33333333.3" }),
    );
    render(<CandidateProfileForm />);
    expect(await screen.findByLabelText("Experience (years)")).toHaveValue("");
    expect(
      screen.getByText("Experience must be between 0 and 20 years."),
    ).toBeInTheDocument();
  });
  it("offers only supported languages", async () => {
    render(<CandidateProfileForm />);
    const select = await screen.findByLabelText("Preferred language");
    expect(
      Array.from((select as HTMLSelectElement).options).map(
        (option) => option.text,
      ),
    ).toEqual([
      "English",
      "Hindi",
      "Kannada",
      "Tamil",
      "Telugu",
      "Malayalam",
      "Marathi",
      "Bengali",
    ]);
  });
  it("rejects an oversized resume before upload", async () => {
    render(<CandidateProfileForm />);
    await screen.findByLabelText("Resume");
    const file = new File([new Uint8Array(5 * 1024 * 1024 + 1)], "resume.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(screen.getByLabelText("Resume"), {
      target: { files: [file] },
    });
    expect(
      await screen.findByText("Resume must be 5 MB or smaller."),
    ).toBeInTheDocument();
  });
  it("uploads a valid resume after saving the profile", async () => {
    const metadata = { file_name: "resume.pdf" };
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) =>
        path.endsWith("/resume") && options?.method === "POST"
          ? Promise.resolve(metadata)
          : path.endsWith("/resume")
            ? Promise.reject(notFound)
            : Promise.resolve(profile),
    );
    render(<CandidateProfileForm />);
    await screen.findByLabelText("Resume");
    fireEvent.change(screen.getByLabelText("Resume"), {
      target: {
        files: [
          new File(["%PDF-1.4"], "resume.pdf", { type: "application/pdf" }),
        ],
      },
    });
    expect(screen.getByText("resume.pdf")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Remove resume.pdf" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await waitFor(() =>
      expect(
        mocks.request.mock.calls.some(
          (call) =>
            call[1]?.method === "POST" && call[1].body instanceof FormData,
        ),
      ).toBe(true),
    );
  });
});
