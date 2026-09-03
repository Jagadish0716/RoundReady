import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CandidateBooking } from "@/components/candidate/candidate-booking";
import { ApiClientError } from "@/lib/api/client";
import * as bookingApi from "@/lib/api/booking";

const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ request: mocks.request }),
}));

const slot = {
  id: "slot-1",
  interviewer_id: "interviewer-1",
  rubric_id: "rubric-1",
  domain: "Backend",
  topic: "Python",
  experience_level: "mid",
  starts_at: "2030-01-01T10:00:00Z",
  ends_at: "2030-01-01T10:20:00Z",
  status: "available",
  hold_expires_at: null,
};
const hold = {
  slot_id: slot.id,
  hold_token: "h".repeat(48),
  expires_at: "2030-01-01T09:55:00Z",
};
const pending = {
  id: "booking-1",
  slot_id: slot.id,
  candidate_id: "candidate-1",
  interviewer_id: slot.interviewer_id,
  starts_at: slot.starts_at,
  ends_at: slot.ends_at,
  status: "payment_pending",
  amount_paise: 20000,
  currency: "INR",
  created_at: "2029-01-01T00:00:00Z",
  updated_at: "2029-01-01T00:00:00Z",
};
const payment = {
  id: "payment-1",
  booking_id: pending.id,
  amount_paise: 20000,
  currency: "INR",
  provider: "development",
  provider_order_id: "order_dev_1",
  provider_payment_id: null,
  status: "pending",
  created_at: "2029-01-01T00:00:00Z",
  updated_at: "2029-01-01T00:00:00Z",
  checkout_data: null,
};

function defaultApi(path: string, options?: { method?: string }): unknown {
  if (path.startsWith("/v1/booking/slots?")) return [slot];
  if (path.endsWith("/hold")) return hold;
  if (path === "/v1/booking/bookings" && options?.method === "POST")
    return pending;
  if (path === "/v1/payments/orders") return payment;
  if (path.endsWith("/development/complete"))
    return { ...payment, status: "captured" };
  if (path.endsWith(pending.id)) return pending;
  throw new Error(`Unexpected path ${path}`);
}

async function discoverAndHold(): Promise<void> {
  fireEvent.click(screen.getByRole("button", { name: "Find slots" }));
  await screen.findByText("Backend · Python");
  fireEvent.click(screen.getByRole("button", { name: "Hold this slot" }));
  await screen.findByText(/Held until/);
}

async function createPendingBooking(): Promise<void> {
  await discoverAndHold();
  fireEvent.click(screen.getByRole("button", { name: "Create booking" }));
  await screen.findByText(/payment pending/i);
}

describe("CandidateBooking", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_DEVELOPMENT_PAYMENTS", "true");
    vi.clearAllMocks();
    mocks.request.mockImplementation((path, options) =>
      Promise.resolve(defaultApi(path, options)),
    );
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("renders available slots with schedule, duration, interviewer and ₹200", async () => {
    render(<CandidateBooking />);
    fireEvent.click(screen.getByRole("button", { name: "Find slots" }));
    expect(await screen.findByText("Backend · Python")).toBeInTheDocument();
    expect(screen.getByText("Interviewer interviewer-1")).toBeInTheDocument();
    expect(screen.getByText("₹200")).toBeInTheDocument();
    expect(screen.getByText(/20 minutes/)).toBeInTheDocument();
  });

  it("holds a selected slot and displays expiry", async () => {
    render(<CandidateBooking />);
    await discoverAndHold();
    expect(mocks.request).toHaveBeenCalledWith(
      "/v1/booking/slots/slot-1/hold",
      { method: "POST" },
    );
  });

  it("shows a slot conflict", async () => {
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) =>
        path.endsWith("/hold")
          ? Promise.reject(
              new ApiClientError(
                "Unavailable",
                409,
                "conflict",
                "slot_unavailable",
                null,
                null,
              ),
            )
          : Promise.resolve(defaultApi(path, options)),
    );
    render(<CandidateBooking />);
    fireEvent.click(screen.getByRole("button", { name: "Find slots" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "Hold this slot" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "no longer available",
    );
  });

  it("creates a PAYMENT_PENDING booking with no candidate id in the request", async () => {
    render(<CandidateBooking />);
    await createPendingBooking();
    expect(mocks.request).toHaveBeenCalledWith(
      "/v1/booking/bookings",
      expect.objectContaining({
        method: "POST",
        body: { slot_id: slot.id, hold_token: hold.hold_token },
      }),
    );
  });

  it("creates an authoritative ₹200 pending payment", async () => {
    render(<CandidateBooking />);
    await createPendingBooking();
    fireEvent.click(
      screen.getByRole("button", { name: "Create ₹200 payment" }),
    );
    expect(await screen.findByText(/^pending$/i)).toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledWith(
      "/v1/payments/orders",
      expect.objectContaining({ body: { booking_id: pending.id } }),
    );
  });

  it("completes development payment and displays only backend-confirmed status", async () => {
    vi.spyOn(bookingApi, "pollBooking").mockResolvedValue({
      ...pending,
      status: "confirmed",
    });
    render(<CandidateBooking />);
    await createPendingBooking();
    fireEvent.click(
      screen.getByRole("button", { name: "Create ₹200 payment" }),
    );
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Complete development payment",
      }),
    );
    expect(await screen.findByText(/^confirmed$/i)).toBeInTheDocument();
    expect(
      screen.getByText("Your interview is confirmed."),
    ).toBeInTheDocument();
    expect(bookingApi.pollBooking).toHaveBeenCalledWith(
      expect.any(Function),
      pending.id,
    );
  });

  it("shows backend payment failure guidance", async () => {
    vi.spyOn(bookingApi, "pollBooking").mockResolvedValue({
      ...pending,
      status: "payment_failed",
    });
    render(<CandidateBooking />);
    await createPendingBooking();
    fireEvent.click(
      screen.getByRole("button", { name: "Create ₹200 payment" }),
    );
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Complete development payment",
      }),
    );
    expect(
      (await screen.findAllByText(/payment failed/i)).length,
    ).toBeGreaterThan(0);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "slot has been released",
    );
  });

  it("reports bounded polling timeout without claiming confirmation", async () => {
    vi.spyOn(bookingApi, "pollBooking").mockResolvedValue({
      ...pending,
      status: "booked",
    });
    render(<CandidateBooking />);
    await createPendingBooking();
    fireEvent.click(
      screen.getByRole("button", { name: "Create ₹200 payment" }),
    );
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Complete development payment",
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "confirmation is still pending",
    );
    expect(screen.queryByText(/^confirmed$/i)).not.toBeInTheDocument();
  });

  it("prevents duplicate hold submission", async () => {
    let resolveHold: ((value: typeof hold) => void) | undefined;
    mocks.request.mockImplementation(
      (path: string, options?: { method?: string }) => {
        if (path.endsWith("/hold"))
          return new Promise((resolve) => {
            resolveHold = resolve;
          });
        return Promise.resolve(defaultApi(path, options));
      },
    );
    render(<CandidateBooking />);
    fireEvent.click(screen.getByRole("button", { name: "Find slots" }));
    const button = await screen.findByRole("button", {
      name: "Hold this slot",
    });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(
      mocks.request.mock.calls.filter(([path]) =>
        String(path).endsWith("/hold"),
      ),
    ).toHaveLength(1);
    resolveHold?.(hold);
    await waitFor(() =>
      expect(screen.getByText(/Held until/)).toBeInTheDocument(),
    );
  });

  it("does not present development completion in production configuration", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.roundready.example");
    vi.stubEnv("NEXT_PUBLIC_ENABLE_DEVELOPMENT_PAYMENTS", "false");
    render(<CandidateBooking />);
    await createPendingBooking();
    fireEvent.click(
      screen.getByRole("button", { name: "Create ₹200 payment" }),
    );
    await screen.findByText(/^pending$/i);
    expect(
      screen.queryByRole("button", { name: "Complete development payment" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/unavailable in this environment/),
    ).toBeInTheDocument();
  });
});

describe("pollBooking", () => {
  it("stops after the configured bounded attempts", async () => {
    const request = vi
      .fn()
      .mockResolvedValue({ ...pending, status: "payment_pending" });
    const result = await bookingApi.pollBooking(request, pending.id, {
      attempts: 3,
      delayMs: 0,
    });
    expect(result.status).toBe("payment_pending");
    expect(request).toHaveBeenCalledTimes(3);
  });
});
