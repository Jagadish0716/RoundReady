import type { ApiRequestOptions } from "@/lib/api/client";
import type { NotificationRecord } from "@/types/notification";

type AuthenticatedRequest = <T>(
  path: string,
  options?: ApiRequestOptions,
) => Promise<T>;

export function listMyNotifications(
  request: AuthenticatedRequest,
): Promise<NotificationRecord[]> {
  return request<NotificationRecord[]>("/v1/notifications/me");
}

export function markNotificationRead(
  request: AuthenticatedRequest,
  notificationId: string,
): Promise<NotificationRecord> {
  return request<NotificationRecord>(
    `/v1/notifications/${notificationId}/read`,
    { method: "PATCH" },
  );
}
