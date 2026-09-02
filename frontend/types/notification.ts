export type NotificationChannel = "email" | "whatsapp";
export type NotificationDeliveryStatus =
  "pending" | "retry_scheduled" | "sent" | "dead_lettered";

export interface NotificationRecord {
  id: string;
  event_type: string;
  channel: NotificationChannel;
  rendered_subject: string | null;
  rendered_body: string;
  status: NotificationDeliveryStatus;
  created_at: string;
  read_at: string | null;
}
