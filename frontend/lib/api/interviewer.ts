import type { ApiRequestOptions } from "@/lib/api/client";
import type {
  Blockout,
  InterviewerProfile,
  InterviewerProfileInput,
  InterviewerSkill,
  InterviewerSkillInput,
  WeeklyRule,
  WeeklyRuleInput,
} from "@/types/interviewer";

export type AuthenticatedRequest = <T>(
  path: string,
  options?: ApiRequestOptions,
) => Promise<T>;
const own = "/v1/interviewers/me";

export const getInterviewerProfile = (request: AuthenticatedRequest) =>
  request<InterviewerProfile>(`${own}/profile`);
export const saveInterviewerProfile = (
  request: AuthenticatedRequest,
  body: InterviewerProfileInput,
) => request<InterviewerProfile>(`${own}/profile`, { method: "PUT", body });
export const getSkills = (request: AuthenticatedRequest) =>
  request<InterviewerSkill[]>(`${own}/skills`);
export const saveSkills = (
  request: AuthenticatedRequest,
  skills: InterviewerSkillInput[],
) =>
  request<InterviewerSkill[]>(`${own}/skills`, {
    method: "PUT",
    body: { skills },
  });
export const getWeeklyRules = (request: AuthenticatedRequest) =>
  request<WeeklyRule[]>(`${own}/availability/weekly`);
export const saveWeeklyRules = (
  request: AuthenticatedRequest,
  rules: WeeklyRuleInput[],
) =>
  request<WeeklyRule[]>(`${own}/availability/weekly`, {
    method: "PUT",
    body: { rules },
  });
export const getBlockouts = (request: AuthenticatedRequest) =>
  request<Blockout[]>(`${own}/availability/blockouts`);
export const createBlockout = (
  request: AuthenticatedRequest,
  body: { starts_at: string; ends_at: string; reason: string | null },
) =>
  request<Blockout>(`${own}/availability/blockouts`, { method: "POST", body });
export const deleteBlockout = (request: AuthenticatedRequest, id: string) =>
  request<null>(`${own}/availability/blockouts/${id}`, { method: "DELETE" });

const admin = "/v1/interviewers/admin";

export const getVerificationQueue = (request: AuthenticatedRequest) =>
  request<InterviewerProfile[]>(`${admin}/verification-queue`);
export const approveInterviewer = (
  request: AuthenticatedRequest,
  interviewerId: string,
) =>
  request<InterviewerProfile>(
    `${admin}/interviewers/${interviewerId}/approve`,
    {
      method: "POST",
    },
  );
export const rejectInterviewer = (
  request: AuthenticatedRequest,
  interviewerId: string,
  reason: string,
) =>
  request<InterviewerProfile>(`${admin}/interviewers/${interviewerId}/reject`, {
    method: "POST",
    body: { reason },
  });
export const suspendInterviewer = (
  request: AuthenticatedRequest,
  interviewerId: string,
  reason: string,
) =>
  request<InterviewerProfile>(
    `${admin}/interviewers/${interviewerId}/suspend`,
    {
      method: "POST",
      body: { reason },
    },
  );
export const reactivateInterviewer = (
  request: AuthenticatedRequest,
  interviewerId: string,
) =>
  request<InterviewerProfile>(
    `${admin}/interviewers/${interviewerId}/reactivate`,
    { method: "POST" },
  );
