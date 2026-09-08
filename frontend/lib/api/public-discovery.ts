import { apiRequest } from "@/lib/api/client";
import type { PublicInterviewer, PublicSlot } from "@/types/public-discovery";

export function listPublicInterviewers() {
  return apiRequest<PublicInterviewer[]>("/v1/public/interviewers");
}

export function listPublicSlots(startsAfter: string, endsBefore: string) {
  const query = new URLSearchParams({
    starts_after: startsAfter,
    ends_before: endsBefore,
  });
  return apiRequest<PublicSlot[]>(`/v1/public/slots?${query.toString()}`);
}
