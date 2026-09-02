"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { ApiClientError } from "@/lib/api/client";
import {
  listMyNotifications,
  markNotificationRead,
} from "@/lib/api/notifications";
import type { NotificationRecord } from "@/types/notification";

function eventLabel(eventType: string): string {
  const labels: Record<string, string> = {
    "booking.confirmed.v1": "Booking confirmed",
    "booking.cancelled.v1": "Booking cancelled",
    "booking.rescheduled.v1": "Booking rescheduled",
    "payment.captured.v1": "Payment confirmed",
    "payment.refunded.v1": "Refund update",
    "interview.interviewer_no_show.v1": "Interviewer attendance update",
    "interview.candidate_no_show.v1": "Candidate attendance update",
    "feedback.submitted.v1": "Feedback available",
  };
  return labels[eventType] ?? eventType;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return error.message;
  return "Unable to load notifications.";
}

export function NotificationCenter() {
  const { request } = useAuth();
  const [notifications, setNotifications] = useState<NotificationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [markingId, setMarkingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setNotifications(await listMyNotifications(request));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    let active = true;
    listMyNotifications(request)
      .then((values) => {
        if (active) setNotifications(values);
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [request]);

  async function markRead(item: NotificationRecord) {
    if (item.read_at || markingId === item.id) return;
    setMarkingId(item.id);
    setError(null);
    try {
      const authoritative = await markNotificationRead(request, item.id);
      setNotifications((current) =>
        current.map((value) =>
          value.id === authoritative.id ? authoritative : value,
        ),
      );
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setMarkingId(null);
    }
  }

  const unread = notifications.filter((item) => !item.read_at).length;

  return (
    <section className="space-y-4" aria-labelledby="notifications-heading">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 id="notifications-heading" className="text-xl font-semibold">
            Notifications
          </h2>
          <p className="text-sm text-slate-600">
            {unread ? `${unread} unread` : "You are all caught up"}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={() => void load()}
          disabled={loading}
        >
          Refresh
        </Button>
      </div>

      {loading && <p role="status">Loading notifications…</p>}
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {!loading && !error && notifications.length === 0 && (
        <p className="rounded-lg border border-dashed p-4 text-sm text-slate-600">
          No notifications yet.
        </p>
      )}
      {!loading && notifications.length > 0 && (
        <ul className="space-y-3">
          {notifications.map((item) => (
            <li
              key={item.id}
              className={`rounded-lg border p-4 ${item.read_at ? "bg-white" : "border-blue-300 bg-blue-50"}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="font-medium">
                    {item.rendered_subject ?? eventLabel(item.event_type)}
                  </p>
                  <p className="text-sm text-slate-700">{item.rendered_body}</p>
                  <p className="text-xs text-slate-500">
                    {new Date(item.created_at).toLocaleString()} ·{" "}
                    {item.channel} · {item.status}
                  </p>
                </div>
                {item.read_at ? (
                  <span className="text-xs text-slate-500">Read</span>
                ) : (
                  <Button
                    type="button"
                    variant="outline"
                    disabled={markingId === item.id}
                    onClick={() => void markRead(item)}
                  >
                    {markingId === item.id ? "Marking…" : "Mark read"}
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
