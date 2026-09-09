import type { ApiRequestOptions } from "@/lib/api/client";
import type {
  ContactChallenge,
  Blockout,
  InterviewerProfile,
  InterviewerProfileInput,
  InterviewerSkill,
  InterviewerSkillInput,
  EvidenceType,
  EvidenceStatus,
  ScreeningStatus,
  VerificationDetail,
  VerificationReviewInput,
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
export const getOwnVerification = (request: AuthenticatedRequest) =>
  request<VerificationDetail>(`${own}/verification`);
export const saveVerificationEvidence = (
  request: AuthenticatedRequest,
  evidence_type: EvidenceType,
  value_reference: string,
) =>
  request<VerificationDetail>(`${own}/verification/evidence`, {
    method: "PUT",
    body: { evidence_type, value_reference },
  });
export const submitVerification = (request: AuthenticatedRequest) =>
  request<InterviewerProfile>(`${own}/verification/submit`, { method: "POST" });

export const requestMobileVerification = (
  request: AuthenticatedRequest,
  mobile: string,
) =>
  request<ContactChallenge>(`${own}/verification/mobile/request`, {
    method: "POST",
    body: { mobile },
  });

export const verifyMobile = (
  request: AuthenticatedRequest,
  challengeId: string,
  secret: string,
) =>
  request<VerificationDetail>(`${own}/verification/mobile/verify`, {
    method: "POST",
    body: { challenge_id: challengeId, secret },
  });

export const requestCompanyEmailVerification = (
  request: AuthenticatedRequest,
  companyEmail: string,
) =>
  request<ContactChallenge>(`${own}/verification/company-email/request`, {
    method: "POST",
    body: { company_email: companyEmail },
  });

export const verifyCompanyEmail = (
  request: AuthenticatedRequest,
  challengeId: string,
  secret: string,
) =>
  request<VerificationDetail>(`${own}/verification/company-email/verify`, {
    method: "POST",
    body: { challenge_id: challengeId, secret },
  });

const admin = "/v1/interviewers/admin";

export const getVerificationQueue = (request: AuthenticatedRequest) =>
  request<InterviewerProfile[]>(`${admin}/verification-queue`);
export const getAllInterviewers = (request: AuthenticatedRequest) =>
  request<InterviewerProfile[]>(`${admin}/interviewers`);
export const getVerificationDetail = (
  request: AuthenticatedRequest,
  interviewerId: string,
) =>
  request<VerificationDetail>(
    `${admin}/interviewers/${interviewerId}/verification`,
  );
export const reviewVerification = (
  request: AuthenticatedRequest,
  interviewerId: string,
  body: VerificationReviewInput,
) =>
  request<VerificationDetail>(
    `${admin}/interviewers/${interviewerId}/verification/review`,
    { method: "POST", body },
  );
export const markLinkedinReviewed = (
  request: AuthenticatedRequest,
  interviewerId: string,
) =>
  request<VerificationDetail>(
    `${admin}/interviewers/${interviewerId}/verification/linkedin-review`,
    { method: "POST" },
  );
export const reviewEvidence = (
  request: AuthenticatedRequest,
  interviewerId: string,
  evidenceId: string,
  status: EvidenceStatus,
  notes?: string,
) =>
  request<VerificationDetail>(
    `${admin}/interviewers/${interviewerId}/verification/evidence/${evidenceId}/review`,
    { method: "POST", body: { status, notes: notes || null } },
  );
export const recordScreening = (
  request: AuthenticatedRequest,
  interviewerId: string,
  screening_status: ScreeningStatus,
  notes?: string,
) =>
  request<VerificationDetail>(
    `${admin}/interviewers/${interviewerId}/verification/screening`,
    {
      method: "POST",
      body: {
        screening_status,
        reviewer_notes: notes || null,
        communication_assessment: null,
        technical_assessment: null,
        overall_result: screening_status,
      },
    },
  );
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
export const deleteInterviewer = (
  request: AuthenticatedRequest,
  interviewerId: string,
  reason: string,
) =>
  request<InterviewerProfile>(`${admin}/interviewers/${interviewerId}/delete`, {
    method: "POST",
    body: { reason },
  });
