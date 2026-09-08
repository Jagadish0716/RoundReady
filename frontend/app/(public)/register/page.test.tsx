import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import RegisterPage from "@/app/(public)/register/page";

vi.mock("@/components/auth/register-form", () => ({
  RegisterForm: () => <div>Registration form</div>,
}));

describe("RegisterPage", () => {
  afterEach(cleanup);

  it("renders the registration form inside its page boundary", () => {
    render(<RegisterPage />);

    expect(screen.getByText("Registration form")).toBeInTheDocument();
  });
});
