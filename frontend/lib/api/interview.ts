import type { ApiRequestOptions } from "@/lib/api/client";
import type {
  FeedbackInput,
  FeedbackReport,
  InterviewSession,
  RoomAccess,
  Rubric,
} from "@/types/interview";

export type AuthenticatedRequest = <T>(
  path: string,
  options?: ApiRequestOptions,
) => Promise<T>;
const sessions = "/v1/interviews/sessions";

export const listSessions = (request: AuthenticatedRequest) =>
  request<InterviewSession[]>(sessions);
export const getSession = (request: AuthenticatedRequest, id: string) =>
  request<InterviewSession>(`${sessions}/${id}`);
export const joinSession = (request: AuthenticatedRequest, id: string) =>
  request<RoomAccess>(`${sessions}/${id}/join`, { method: "POST" });
export const getRubric = (request: AuthenticatedRequest, id: string) =>
  request<Rubric>(`${sessions}/${id}/rubric`);
export const startSession = (request: AuthenticatedRequest, id: string) =>
  request<InterviewSession>(`${sessions}/${id}/start`, { method: "POST" });
export const completeSession = (request: AuthenticatedRequest, id: string) =>
  request<InterviewSession>(`${sessions}/${id}/complete`, { method: "POST" });
export const submitFeedback = (
  request: AuthenticatedRequest,
  id: string,
  body: FeedbackInput,
) =>
  request<FeedbackReport>(`${sessions}/${id}/feedback`, {
    method: "POST",
    body,
  });
export const getFeedback = (request: AuthenticatedRequest, id: string) =>
  request<FeedbackReport>(`${sessions}/${id}/feedback`);
