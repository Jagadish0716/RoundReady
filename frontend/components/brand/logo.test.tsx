import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Logo } from "@/components/brand/logo";

describe("Logo", () => {
  afterEach(cleanup);

  it("renders accessible responsive brand images", () => {
    render(<Logo />);
    const images = screen.getAllByRole("img", { name: "RoundReady" });
    expect(images).toHaveLength(2);
    expect(images[0]).toHaveAttribute(
      "src",
      expect.stringContaining("favicon-32x32.png"),
    );
    expect(images[1]).toHaveAttribute(
      "src",
      expect.stringContaining("roundready-horizontal-logo.png"),
    );
  });

  it("supports an explicit symbol variant", () => {
    render(<Logo variant="symbol" />);
    expect(screen.getByRole("img", { name: "RoundReady" })).toHaveAttribute(
      "width",
      "32",
    );
  });
});
