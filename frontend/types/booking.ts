export type SlotStatus = "available" | "held" | "booked" | "blocked";
export type BookingStatus =
  | "payment_pending"
  | "booked"
  | "confirmed"
  | "ready"
  | "in_progress"
  | "completed"
  | "feedback_pending"
  | "feedback_submitted"
  | "settled"
  | "cancelled"
  | "payment_failed"
  | "candidate_no_show"
  | "interviewer_no_show"
  | "technical_failure"
  | "refunded"
  | "rescheduled";

export interface InterviewSlot {
  id: string;
  interviewer_id: string;
  rubric_id: string;
  domain: string;
  topic: string;
  experience_level: string;
  starts_at: string;
  ends_at: string;
  status: SlotStatus;
  hold_expires_at: string | null;
}

export interface SlotHold {
  slot_id: string;
  hold_token: string;
  expires_at: string;
}

export interface Booking {
  id: string;
  slot_id: string;
  candidate_id: string;
  interviewer_id: string;
  starts_at: string;
  ends_at: string;
  status: BookingStatus;
  amount_paise: number;
  currency: string;
  created_at: string;
  updated_at: string;
}

export type PaymentStatus =
  | "created"
  | "pending"
  | "authorized"
  | "captured"
  | "failed"
  | "refund_pending"
  | "refunded"
  | "partially_refunded";

export interface Payment {
  id: string;
  booking_id: string;
  amount_paise: number;
  currency: string;
  provider: string;
  provider_order_id: string | null;
  provider_payment_id: string | null;
  status: PaymentStatus;
  created_at: string;
  updated_at: string;
  checkout_data: Record<string, string | number> | null;
}
