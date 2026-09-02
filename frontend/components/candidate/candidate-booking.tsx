"use client";

import { useMemo, useRef, useState, type FormEvent } from "react";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiClientError } from "@/lib/api/client";
import * as api from "@/lib/api/booking";
import { developmentPaymentsEnabled } from "@/lib/config";
import type {
  Booking,
  InterviewSlot,
  Payment,
  SlotHold,
} from "@/types/booking";

const SESSION_PRICE_PAISE = 20000;

function dateValue(offsetDays: number): string {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

function formatMoney(amount: number, currency: string): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount / 100);
}

function durationMinutes(slot: InterviewSlot | Booking): number {
  return Math.round(
    (new Date(slot.ends_at).getTime() - new Date(slot.starts_at).getTime()) /
      60000,
  );
}

function messageFor(error: unknown): string {
  if (!(error instanceof ApiClientError))
    return "The request could not be completed.";
  if (error.status === 409) {
    if (error.code === "invalid_or_expired_hold")
      return "Your slot hold expired. Search and hold the slot again.";
    return "This slot is no longer available. Refresh the slot list and choose another.";
  }
  if (error.status === 422) return "The request contains invalid values.";
  return error.message;
}

export function CandidateBooking() {
  const { request } = useAuth();
  const [from, setFrom] = useState(() => dateValue(0));
  const [to, setTo] = useState(() => dateValue(30));
  const [slots, setSlots] = useState<InterviewSlot[]>([]);
  const [selected, setSelected] = useState<InterviewSlot | null>(null);
  const [hold, setHold] = useState<SlotHold | null>(null);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [payment, setPayment] = useState<Payment | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const bookingKey = useRef(crypto.randomUUID());
  const paymentKey = useRef(crypto.randomUUID());
  const development = developmentPaymentsEnabled();

  const authoritativePrice = useMemo(() => {
    const source = payment ?? booking;
    return source ? formatMoney(source.amount_paise, source.currency) : "₹200";
  }, [booking, payment]);

  async function search(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setBusy("search");
    setError(null);
    setNotice(null);
    try {
      const starts = new Date(`${from}T00:00:00`).toISOString();
      const ends = new Date(`${to}T23:59:59`).toISOString();
      if (starts >= ends) throw new Error("Choose a valid date range.");
      setSlots(await api.listSlots(request, starts, ends));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : messageFor(caught));
    } finally {
      setBusy(null);
    }
  }

  async function selectSlot(slot: InterviewSlot) {
    if (busy) return;
    setBusy(`hold-${slot.id}`);
    setError(null);
    setNotice(null);
    try {
      const held = await api.holdSlot(request, slot.id);
      setSelected(slot);
      setHold(held);
      setBooking(null);
      setPayment(null);
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(null);
    }
  }

  async function book() {
    if (!selected || !hold || busy) return;
    setBusy("booking");
    setError(null);
    try {
      const created = await api.createBooking(
        request,
        selected.id,
        hold.hold_token,
        bookingKey.current,
      );
      if (
        created.amount_paise !== SESSION_PRICE_PAISE ||
        created.currency !== "INR"
      )
        throw new Error(
          "The booking price does not match the ₹200 session price.",
        );
      setBooking(created);
      setNotice("Booking created. Payment is required to confirm it.");
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(null);
    }
  }

  async function startPayment() {
    if (!booking || busy) return;
    setBusy("payment");
    setError(null);
    try {
      const created = await api.createPayment(
        request,
        booking.id,
        paymentKey.current,
      );
      if (
        created.amount_paise !== booking.amount_paise ||
        created.currency !== booking.currency
      )
        throw new Error(
          "Payment amount does not match the authoritative booking amount.",
        );
      setPayment(created);
      setNotice("Payment order created and awaiting completion.");
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(null);
    }
  }

  async function completePayment() {
    if (!booking || !payment || busy || !development) return;
    setBusy("complete");
    setError(null);
    setNotice("Waiting for booking confirmation…");
    try {
      const completed = await api.completeDevelopmentPayment(
        request,
        payment.id,
      );
      setPayment(completed);
      const refreshed = await api.pollBooking(request, booking.id);
      setBooking(refreshed);
      if (refreshed.status === "confirmed")
        setNotice("Your interview is confirmed.");
      else if (refreshed.status === "payment_failed")
        setError(
          "Payment failed. The slot has been released; choose another available slot.",
        );
      else
        setError(
          "Payment was received, but booking confirmation is still pending. Check again shortly.",
        );
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Book a mock interview</h1>
        <p className="mt-1 text-sm text-neutral-600">
          Find a 20-minute interview slot and confirm it securely for ₹200.
        </p>
      </header>
      {error ? (
        <p
          role="alert"
          className="rounded-md bg-red-50 p-3 text-sm text-red-800"
        >
          {error}
        </p>
      ) : null}
      {notice ? (
        <p
          role="status"
          className="rounded-md bg-blue-50 p-3 text-sm text-blue-800"
        >
          {notice}
        </p>
      ) : null}

      <form
        className="flex flex-wrap items-end gap-3 rounded-lg border bg-white p-4"
        onSubmit={search}
      >
        <div>
          <Label htmlFor="slots-from">From</Label>
          <Input
            className="mt-2"
            id="slots-from"
            type="date"
            value={from}
            onChange={(event) => setFrom(event.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="slots-to">To</Label>
          <Input
            className="mt-2"
            id="slots-to"
            type="date"
            value={to}
            onChange={(event) => setTo(event.target.value)}
          />
        </div>
        <Button type="submit" disabled={busy !== null}>
          {busy === "search" ? "Searching…" : "Find slots"}
        </Button>
      </form>

      {slots.length === 0 ? (
        <p className="text-sm text-neutral-600">No available slots loaded.</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {slots.map((slot) => (
            <article className="rounded-lg border bg-white p-4" key={slot.id}>
              <div className="flex justify-between gap-4">
                <div>
                  <h2 className="font-semibold">
                    {slot.domain} · {slot.topic}
                  </h2>
                  <p className="text-sm text-neutral-600">
                    Interviewer {slot.interviewer_id}
                  </p>
                </div>
                <span className="font-semibold">₹200</span>
              </div>
              <p className="mt-3 text-sm">
                {new Date(slot.starts_at).toLocaleString()} ·{" "}
                {durationMinutes(slot)} minutes
              </p>
              <p className="mt-1 text-sm text-green-700 capitalize">
                {slot.status}
              </p>
              <Button
                className="mt-3"
                type="button"
                disabled={busy !== null || slot.status !== "available"}
                onClick={() => void selectSlot(slot)}
              >
                {busy === `hold-${slot.id}` ? "Holding…" : "Hold this slot"}
              </Button>
            </article>
          ))}
        </div>
      )}

      {selected && hold ? (
        <section className="rounded-lg border bg-white p-4">
          <h2 className="font-semibold">Selected slot</h2>
          <p className="mt-1 text-sm">
            {selected.domain} · {selected.topic} ·{" "}
            {new Date(selected.starts_at).toLocaleString()}
          </p>
          <p className="mt-1 text-sm">
            Held until {new Date(hold.expires_at).toLocaleTimeString()}
          </p>
          {!booking ? (
            <Button
              className="mt-3"
              type="button"
              disabled={busy !== null}
              onClick={() => void book()}
            >
              {busy === "booking" ? "Creating booking…" : "Create booking"}
            </Button>
          ) : null}
        </section>
      ) : null}

      {booking ? (
        <section
          className="space-y-3 rounded-lg border bg-white p-4"
          aria-label="Booking status"
        >
          <div className="flex justify-between">
            <h2 className="font-semibold">Booking {booking.id}</h2>
            <strong className="uppercase">
              {booking.status.replaceAll("_", " ")}
            </strong>
          </div>
          <p className="text-sm">Interviewer {booking.interviewer_id}</p>
          <p className="text-sm">
            {new Date(booking.starts_at).toLocaleString()} ·{" "}
            {durationMinutes(booking)} minutes · {authoritativePrice}
          </p>
          {booking.status === "payment_pending" && !payment ? (
            <Button
              type="button"
              disabled={busy !== null}
              onClick={() => void startPayment()}
            >
              {busy === "payment"
                ? "Creating payment…"
                : `Create ${authoritativePrice} payment`}
            </Button>
          ) : null}
          {payment ? (
            <p className="text-sm">
              Payment:{" "}
              <strong className="uppercase">
                {payment.status.replaceAll("_", " ")}
              </strong>
            </p>
          ) : null}
          {booking.status === "payment_pending" && payment && development ? (
            <Button
              type="button"
              disabled={busy !== null}
              onClick={() => void completePayment()}
            >
              {busy === "complete"
                ? "Confirming…"
                : "Complete development payment"}
            </Button>
          ) : null}
          {booking.status === "payment_pending" && payment && !development ? (
            <p className="text-sm text-neutral-600">
              Development payment completion is unavailable in this environment.
            </p>
          ) : null}
          {booking.status === "confirmed" ? (
            <p className="text-sm text-green-700">
              Your slot is confirmed. Interview access will be available closer
              to the scheduled time.
            </p>
          ) : null}
          {booking.status === "payment_failed" ? (
            <p className="text-sm text-red-700">
              Payment failed. Search again to choose an available slot.
            </p>
          ) : null}
        </section>
      ) : null}
    </section>
  );
}
