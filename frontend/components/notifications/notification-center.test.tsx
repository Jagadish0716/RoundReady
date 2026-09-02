import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NotificationCenter } from "@/components/notifications/notification-center";
import { ApiClientError } from "@/lib/api/client";
import type { NotificationRecord } from "@/types/notification";

const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ request: mocks.request }),
}));

const unread: NotificationRecord = {
  id: "11111111-1111-4111-8111-111111111111",
  event_type: "feedback.submitted.v1",
  channel: "email",
  rendered_subject: "Your interview feedback is available",
  rendered_body: "Feedback for your interview is now available in RoundReady.",
  status: "sent",
  created_at: "2026-09-02T10:00:00Z",
  read_at: null,
};

describe("NotificationCenter", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  it("shows loading then the empty state", async () => {
    let resolve: ((value: NotificationRecord[]) => void) | undefined;
    mocks.request.mockReturnValue(
      new Promise<NotificationRecord[]>((done) => {
        resolve = done;
      }),
    );
    render(<NotificationCenter />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading notifications",
    );
    resolve?.([]);
    expect(
      await screen.findByText("No notifications yet."),
    ).toBeInTheDocument();
  });

  it("renders feedback and authoritative delivery status as unread", async () => {
    mocks.request.mockResolvedValue([unread]);
    render(<NotificationCenter />);
    expect(
      await screen.findByText(unread.rendered_subject!),
    ).toBeInTheDocument();
    expect(screen.getByText(unread.rendered_body)).toBeInTheDocument();
    expect(screen.getByText("1 unread")).toBeInTheDocument();
    expect(screen.getByText(/email · sent/)).toBeInTheDocument();
  });

  it("renders booking and payment notification titles", async () => {
    mocks.request.mockResolvedValue([
      {
        ...unread,
        id: "booking",
        event_type: "booking.confirmed.v1",
        rendered_subject: null,
      },
      {
        ...unread,
        id: "payment",
        event_type: "payment.captured.v1",
        rendered_subject: null,
      },
    ]);
    render(<NotificationCenter />);
    expect(await screen.findByText("Booking confirmed")).toBeInTheDocument();
    expect(screen.getByText("Payment confirmed")).toBeInTheDocument();
  });

  it("marks an owned notification read using only its notification ID", async () => {
    const marked = { ...unread, read_at: "2026-09-02T10:05:00Z" };
    mocks.request.mockResolvedValueOnce([unread]).mockResolvedValueOnce(marked);
    render(<NotificationCenter />);
    fireEvent.click(await screen.findByRole("button", { name: "Mark read" }));
    expect(await screen.findByText("Read")).toBeInTheDocument();
    expect(mocks.request).toHaveBeenLastCalledWith(
      `/v1/notifications/${unread.id}/read`,
      { method: "PATCH" },
    );
    expect(JSON.stringify(mocks.request.mock.calls)).not.toContain("recipient");
  });

  it("does not offer or request mark-read for an already-read item", async () => {
    mocks.request.mockResolvedValue([
      { ...unread, read_at: "2026-09-02T10:05:00Z" },
    ]);
    render(<NotificationCenter />);
    expect(await screen.findByText("Read")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Mark read" }),
    ).not.toBeInTheDocument();
    expect(mocks.request).toHaveBeenCalledTimes(1);
  });

  it("prevents duplicate mark-read requests while one is pending", async () => {
    mocks.request
      .mockResolvedValueOnce([unread])
      .mockReturnValueOnce(new Promise(() => undefined));
    render(<NotificationCenter />);
    const button = await screen.findByRole("button", { name: "Mark read" });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(button).toBeDisabled());
    expect(mocks.request).toHaveBeenCalledTimes(2);
  });

  it("shows API errors without exposing notification data", async () => {
    mocks.request.mockRejectedValue(
      new ApiClientError(
        "Notifications unavailable",
        503,
        "server",
        "unavailable",
        null,
        null,
      ),
    );
    render(<NotificationCenter />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Notifications unavailable",
    );
  });
});
