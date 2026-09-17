import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HeroSlider } from "@/components/public/hero-slider";

describe("HeroSlider", () => {
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("rotates every five seconds and resets after manual selection", () => {
    vi.useFakeTimers();
    render(<HeroSlider />);

    expect(
      screen.getByRole("heading", {
        name: "Better interview preparation. A brighter you.",
      }),
    ).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(5000));
    expect(
      screen.getByRole("heading", { name: "Learn from industry experts." }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /show slide 3/i }));
    act(() => vi.advanceTimersByTime(4999));
    expect(
      screen.getByRole("heading", {
        name: "Affordable practice. Real career progress.",
      }),
    ).toBeInTheDocument();
  });

  it("pauses on hover and supports keyboard navigation", () => {
    vi.useFakeTimers();
    render(<HeroSlider />);
    const carousel = screen.getByRole("region", {
      name: "Why candidates choose RoundReady",
    });

    fireEvent.mouseEnter(carousel);
    act(() => vi.advanceTimersByTime(6000));
    expect(
      screen.getByRole("heading", {
        name: "Better interview preparation. A brighter you.",
      }),
    ).toBeInTheDocument();

    fireEvent.keyDown(carousel, { key: "ArrowRight" });
    expect(
      screen.getByRole("heading", { name: "Learn from industry experts." }),
    ).toBeInTheDocument();
    fireEvent.keyDown(carousel, { key: "ArrowLeft" });
    expect(
      screen.getByRole("heading", {
        name: "Better interview preparation. A brighter you.",
      }),
    ).toBeInTheDocument();
  });
});
