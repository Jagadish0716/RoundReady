"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import Link from "next/link";
import {
  CalendarDays,
  CheckCircle2,
  Clock3,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiClientError } from "@/lib/api/client";
import * as api from "@/lib/api/booking";
import { developmentPaymentsEnabled } from "@/lib/config";
import { openRazorpayCheckout } from "@/lib/payments/razorpay";
import type {
  Booking,
  InterviewSlot,
  Payment,
  SlotHold,
} from "@/types/booking";

const SESSION_PRICE_PAISE = 20000;
const CHECKOUT_SESSION_KEY = "roundready.checkout";

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

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(value));
}

function formatTimeRange(value: InterviewSlot | Booking): string {
  const formatter = new Intl.DateTimeFormat("en-IN", {
    hour: "numeric",
    minute: "2-digit",
  });
  return `${formatter.format(new Date(value.starts_at))} – ${formatter.format(new Date(value.ends_at))}`;
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

export function CandidateBooking({
  intentSlotId,
  intentInterviewerId,
}: {
  intentSlotId?: string;
  intentInterviewerId?: string;
}) {
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
  const intentHandled = useRef(false);
  const restored = useRef(false);
  const development = developmentPaymentsEnabled();

  const authoritativePrice = useMemo(() => {
    const source = payment ?? booking;
    return source ? formatMoney(source.amount_paise, source.currency) : "₹200";
  }, [booking, payment]);

  useEffect(() => {
    if (restored.current) return;
    restored.current = true;
    const saved = window.sessionStorage.getItem(CHECKOUT_SESSION_KEY);
    if (!saved) return;
    void Promise.resolve().then(async () => {
      try {
        const context = JSON.parse(saved) as {
          bookingId?: string;
          paymentId?: string;
        };
        if (!context.bookingId) return;
        setBusy("restore");
        const restoredBooking = await api.getBooking(
          request,
          context.bookingId,
        );
        setBooking(restoredBooking);
        if (context.paymentId) {
          const restoredPayment = await api.getPayment(
            request,
            context.paymentId,
          );
          setPayment(restoredPayment);
          if (restoredPayment.status === "captured") {
            setBooking(await api.pollBooking(request, restoredBooking.id));
          }
        }
        setNotice("Your checkout was restored securely.");
      } catch {
        window.sessionStorage.removeItem(CHECKOUT_SESSION_KEY);
      } finally {
        setBusy(null);
      }
    });
  }, [request]);

  function rememberCheckout(nextBooking: Booking, nextPayment?: Payment) {
    window.sessionStorage.setItem(
      CHECKOUT_SESSION_KEY,
      JSON.stringify({
        bookingId: nextBooking.id,
        paymentId: nextPayment?.id,
      }),
    );
  }

  useEffect(() => {
    if (!intentSlotId || !intentInterviewerId || intentHandled.current) return;
    intentHandled.current = true;
    void Promise.resolve().then(async () => {
      setBusy("revalidate");
      setError(null);
      try {
        const slot = await api.getPublicSlot(request, intentSlotId);
        if (slot.interviewer_id !== intentInterviewerId)
          throw new Error("invalid booking context");
        bookingKey.current = crypto.randomUUID();
        paymentKey.current = crypto.randomUUID();
        const held = await api.holdSlot(request, slot.id);
        setSelected(slot);
        setHold(held);
        setSlots([slot]);
        setNotice("Slot availability was revalidated and is now held for you.");
      } catch {
        setError(
          "This slot is no longer available. Choose another verified interviewer or slot.",
        );
      } finally {
        setBusy(null);
      }
    });
  }, [intentInterviewerId, intentSlotId, request]);

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
      bookingKey.current = crypto.randomUUID();
      paymentKey.current = crypto.randomUUID();
      const held = await api.holdSlot(request, slot.id);
      setSelected(slot);
      setHold(held);
      setBooking(null);
      setPayment(null);
      window.sessionStorage.removeItem(CHECKOUT_SESSION_KEY);
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
      rememberCheckout(created);
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
        created.currency !== booking.currency ||
        created.interviewer_earning_paise !== 15000 ||
        created.platform_fee_paise !== 5000
      )
        throw new Error(
          "Payment amount does not match the authoritative booking amount.",
        );
      setPayment(created);
      rememberCheckout(booking, created);
      if (development) {
        setNotice("Payment order created and awaiting local completion.");
      } else {
        await launchCheckout(created);
      }
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(null);
    }
  }

  async function reconcilePayment(current: Payment) {
    if (!booking) return;
    setNotice("Payment submitted. Waiting for secure confirmation…");
    const refreshedPayment = ["captured", "failed", "refunded"].includes(
      current.status,
    )
      ? current
      : await api.pollPayment(request, current.id);
    setPayment(refreshedPayment);
    if (refreshedPayment.status === "captured") {
      const refreshedBooking = await api.pollBooking(request, booking.id);
      setBooking(refreshedBooking);
      if (refreshedBooking.status === "confirmed") {
        setNotice("Payment successful. Your interview is confirmed.");
      } else if (refreshedBooking.status === "payment_failed") {
        setError(
          "Payment failed. The slot has been released; choose another available slot.",
        );
      } else {
        setError(
          "Payment was received, but booking confirmation is still pending. Check again shortly.",
        );
      }
      return;
    }
    if (refreshedPayment.status === "failed") {
      setError(
        "Payment wasn't completed. Your booking has not been confirmed.",
      );
      return;
    }
    setError(
      "Payment confirmation is taking longer than expected. You can safely check again.",
    );
  }

  async function launchCheckout(current: Payment) {
    if (!booking || busy === "checkout") return;
    const checkout = current.checkout_data;
    if (
      current.provider !== "razorpay" ||
      !checkout ||
      typeof checkout.key_id !== "string" ||
      typeof checkout.order_id !== "string" ||
      checkout.amount !== SESSION_PRICE_PAISE ||
      checkout.currency !== "INR"
    ) {
      setError(
        "Secure payment checkout is temporarily unavailable. Please try again.",
      );
      return;
    }
    setBusy("checkout");
    setError(null);
    try {
      const outcome = await openRazorpayCheckout({
        key_id: checkout.key_id,
        order_id: checkout.order_id,
        amount: checkout.amount,
        currency: checkout.currency,
      });
      if (outcome === "dismissed") {
        setError(
          "Payment wasn't completed. Your booking has not been confirmed.",
        );
        return;
      }
      await reconcilePayment(current);
    } catch {
      setError(
        "Secure payment checkout could not be opened. Please check your connection and try again.",
      );
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
      await reconcilePayment(completed);
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
                  {slot.roundready_verified ? (
                    <p className="mt-1 text-xs font-medium text-green-700">
                      RoundReady Verified
                    </p>
                  ) : null}
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
          className="overflow-hidden rounded-[1.75rem] border border-blue-100 bg-white shadow-[0_24px_65px_-42px_rgba(30,64,175,0.5)]"
          aria-label="Booking status"
        >
          <div className="border-b border-slate-100 bg-gradient-to-r from-blue-50 to-white px-5 py-5 sm:px-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-bold tracking-wider text-blue-700 uppercase">
                  Secure checkout
                </p>
                <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">
                  {booking.status === "confirmed"
                    ? "Payment successful"
                    : "Confirm your interview"}
                </h2>
              </div>
              <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-slate-700 uppercase shadow-sm ring-1 ring-slate-200">
                {booking.status.replaceAll("_", " ")}
              </span>
            </div>
          </div>
          <div className="grid gap-7 p-5 sm:p-8 md:grid-cols-[1fr_0.9fr]">
            <div className="space-y-5">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
                  <UserRound className="h-5 w-5" aria-hidden />
                </span>
                <div>
                  <p className="text-xs font-medium text-slate-500">
                    Interviewer
                  </p>
                  <p className="font-semibold text-slate-950">
                    Verified RoundReady professional
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {selected
                      ? `${selected.domain} • ${selected.topic}`
                      : `Reference ${booking.interviewer_id.slice(0, 8)}`}
                  </p>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-1 lg:grid-cols-2">
                <CheckoutDetail
                  icon={<CalendarDays aria-hidden />}
                  label="Date"
                  value={formatDate(booking.starts_at)}
                />
                <CheckoutDetail
                  icon={<Clock3 aria-hidden />}
                  label="Time"
                  value={formatTimeRange(booking)}
                />
              </div>
              <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
                <div className="flex justify-between gap-4">
                  <span>Interview fee</span>
                  <strong className="text-slate-950">
                    {authoritativePrice}
                  </strong>
                </div>
                <p className="mt-3">
                  {payment
                    ? formatMoney(
                        payment.interviewer_earning_paise,
                        payment.currency,
                      )
                    : "₹150"}{" "}
                  is the interviewer earning
                </p>
                <p className="mt-1">
                  {payment
                    ? formatMoney(payment.platform_fee_paise, payment.currency)
                    : "₹50"}{" "}
                  helps run RoundReady
                </p>
                <p className="mt-3 text-xs">
                  Interviewer payout status: pending
                </p>
              </div>
            </div>

            <div className="flex flex-col rounded-2xl border border-blue-100 bg-blue-50/60 p-5">
              {booking.status === "confirmed" ? (
                <>
                  <CheckCircle2
                    className="h-10 w-10 text-emerald-600"
                    aria-hidden
                  />
                  <h3 className="mt-4 text-xl font-bold text-slate-950">
                    Your interview is confirmed.
                  </h3>
                  <dl className="mt-5 space-y-3 text-sm">
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-600">Amount paid</dt>
                      <dd className="font-bold">{authoritativePrice}</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-600">Duration</dt>
                      <dd className="font-semibold">
                        {durationMinutes(booking)} minutes
                      </dd>
                    </div>
                  </dl>
                  <Button
                    asChild
                    className="mt-6 h-12 rounded-xl bg-blue-600 hover:bg-blue-700"
                  >
                    <Link href="/candidate/bookings">View my booking</Link>
                  </Button>
                </>
              ) : (
                <>
                  <div className="flex items-center justify-between gap-4 border-b border-blue-100 pb-4">
                    <span className="font-semibold text-slate-700">Total</span>
                    <strong className="text-3xl text-slate-950">
                      {authoritativePrice}
                    </strong>
                  </div>
                  {payment ? (
                    <p className="mt-4 text-sm text-slate-600">
                      Payment status:{" "}
                      <strong className="text-slate-900 uppercase">
                        {payment.status.replaceAll("_", " ")}
                      </strong>
                    </p>
                  ) : null}
                  {booking.status === "payment_pending" && !payment ? (
                    <Button
                      type="button"
                      className="mt-5 h-13 rounded-xl bg-blue-600 text-base hover:bg-blue-700"
                      disabled={busy !== null}
                      onClick={() => void startPayment()}
                    >
                      {busy === "payment"
                        ? "Preparing secure checkout…"
                        : `Pay ${authoritativePrice} securely`}
                    </Button>
                  ) : null}
                  {booking.status === "payment_pending" &&
                  payment &&
                  development ? (
                    <Button
                      type="button"
                      className="mt-5 h-13 rounded-xl bg-blue-600 text-base hover:bg-blue-700"
                      disabled={busy !== null}
                      onClick={() => void completePayment()}
                    >
                      {busy === "complete"
                        ? "Confirming…"
                        : "Complete development payment"}
                    </Button>
                  ) : null}
                  {booking.status === "payment_pending" &&
                  payment &&
                  !development ? (
                    <Button
                      type="button"
                      className="mt-5 h-13 rounded-xl bg-blue-600 text-base hover:bg-blue-700"
                      disabled={busy !== null}
                      onClick={() => void launchCheckout(payment)}
                    >
                      {busy === "checkout"
                        ? "Opening Razorpay…"
                        : `Pay ${authoritativePrice} securely`}
                    </Button>
                  ) : null}
                  {booking.status === "payment_failed" ? (
                    <Button asChild className="mt-5 h-12 rounded-xl">
                      <Link href="/candidate">Choose another slot</Link>
                    </Button>
                  ) : null}
                  <div className="mt-auto pt-5 text-center">
                    <p className="inline-flex items-center gap-2 text-xs font-medium text-slate-600">
                      <ShieldCheck className="h-4 w-4" aria-hidden />
                      Secure payment powered by Razorpay
                    </p>
                    <p className="mt-2 text-xs text-slate-500">
                      UPI, QR and available payment options are handled securely
                      by Razorpay.
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        </section>
      ) : null}
    </section>
  );
}

function CheckoutDetail({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 text-blue-700 [&>svg]:h-5 [&>svg]:w-5">
        {icon}
      </span>
      <div>
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <p className="mt-0.5 text-sm font-semibold text-slate-950">{value}</p>
      </div>
    </div>
  );
}
