import type { ApiRequestOptions } from "@/lib/api/client";
import type {
  Booking,
  InterviewSlot,
  Payment,
  SlotHold,
} from "@/types/booking";

export type AuthenticatedRequest = <T>(
  path: string,
  options?: ApiRequestOptions,
) => Promise<T>;

export function listSlots(
  request: AuthenticatedRequest,
  startsAfter: string,
  endsBefore: string,
) {
  const query = new URLSearchParams({
    starts_after: startsAfter,
    ends_before: endsBefore,
  });
  return request<InterviewSlot[]>(`/v1/booking/slots?${query.toString()}`);
}

export function holdSlot(request: AuthenticatedRequest, slotId: string) {
  return request<SlotHold>(`/v1/booking/slots/${slotId}/hold`, {
    method: "POST",
  });
}

export function createBooking(
  request: AuthenticatedRequest,
  slotId: string,
  holdToken: string,
  idempotencyKey: string,
) {
  return request<Booking>("/v1/booking/bookings", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: { slot_id: slotId, hold_token: holdToken },
  });
}

export function getBooking(request: AuthenticatedRequest, bookingId: string) {
  return request<Booking>(`/v1/booking/bookings/${bookingId}`);
}

export function createPayment(
  request: AuthenticatedRequest,
  bookingId: string,
  idempotencyKey: string,
) {
  return request<Payment>("/v1/payments/orders", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: { booking_id: bookingId },
  });
}

export function completeDevelopmentPayment(
  request: AuthenticatedRequest,
  paymentId: string,
) {
  return request<Payment>(`/v1/payments/${paymentId}/development/complete`, {
    method: "POST",
  });
}

export async function pollBooking(
  request: AuthenticatedRequest,
  bookingId: string,
  options: { attempts?: number; delayMs?: number } = {},
): Promise<Booking> {
  const attempts = options.attempts ?? 10;
  const delayMs = options.delayMs ?? 1000;
  let booking = await getBooking(request, bookingId);
  for (let attempt = 1; attempt < attempts; attempt += 1) {
    if (["confirmed", "payment_failed", "cancelled"].includes(booking.status))
      return booking;
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    booking = await getBooking(request, bookingId);
  }
  return booking;
}
