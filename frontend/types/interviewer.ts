export const interviewerDomains = [
  "DevOps",
  "AWS",
  "Azure",
  "Backend",
  "Full Stack",
  "QA",
  "Tech Support",
] as const;

export type InterviewerDomain = (typeof interviewerDomains)[number];
export type VerificationStatus =
  "pending" | "under_review" | "verified" | "rejected" | "suspended";
export type VerificationCheckType =
  | "email_verified"
  | "mobile_verified"
  | "linkedin_reviewed"
  | "company_email_verified"
  | "professional_evidence_reviewed"
  | "screening_call_passed";
export type EvidenceType =
  "linkedin" | "company_email" | "github_or_portfolio" | "supporting_document";
export type EvidenceStatus = "pending" | "verified" | "rejected";
export type ScreeningStatus = "not_scheduled" | "pending" | "passed" | "failed";

export interface VerificationEvidence {
  id: string;
  evidence_type: EvidenceType;
  value_reference: string;
  status: EvidenceStatus;
  reviewer_notes: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface VerificationCheck {
  check_type: VerificationCheckType;
  passed: boolean;
  reviewed_at: string | null;
}

export interface ScreeningResult {
  screening_status: ScreeningStatus;
  reviewer_notes: string | null;
  communication_assessment: string | null;
  technical_assessment: string | null;
  overall_result: string | null;
  reviewed_at: string | null;
}

export interface VerificationHistory {
  action: string;
  from_status: VerificationStatus | null;
  to_status: VerificationStatus;
  reviewed_by: string;
  notes: string | null;
  created_at: string;
}

export interface VerificationDetail {
  interviewer_id: string;
  status: VerificationStatus;
  submitted_at: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  suspension_reason: string | null;
  evidence: VerificationEvidence[];
  checks: VerificationCheck[];
  screening: ScreeningResult | null;
  history: VerificationHistory[];
  account_email?: string | null;
  account_email_verified?: boolean;
  mobile_e164?: string | null;
  mobile_verified?: boolean;
  company_email?: string | null;
  company_email_verified?: boolean;
}

export interface ContactChallenge {
  challenge_id: string;
  expires_at: string;
  resend_available_at: string;
  development_secret: string | null;
}

export interface VerificationReviewInput {
  action:
    | "under_review"
    | "verify"
    | "reject"
    | "request_more_evidence"
    | "suspend"
    | "reactivate";
  reason?: string;
  checks?: Partial<Record<VerificationCheckType, boolean>>;
  evidence_statuses?: Record<string, EvidenceStatus>;
  screening?: Omit<ScreeningResult, "reviewed_at">;
}

export interface InterviewerProfileInput {
  full_name: string;
  headline: string;
  company: string | null;
  job_title: string | null;
  experience_years: string;
  linkedin_url: string | null;
  github_url: string | null;
  bio: string | null;
}

export interface InterviewerProfile extends Omit<
  InterviewerProfileInput,
  "full_name"
> {
  full_name: string | null;
  user_id: string;
  verification_status: VerificationStatus;
  verification_reason: string | null;
  rating_average: string;
  rating_count: number;
  completed_interviews: number;
  reliability_score: string;
  created_at: string;
  updated_at: string;
}

export interface InterviewerSkillInput {
  domain: InterviewerDomain;
  topic: string;
  skill_name: string;
  experience_years: string;
}

export interface InterviewerSkill extends InterviewerSkillInput {
  id: string;
}

export interface WeeklyRuleInput {
  weekday: number;
  start_time: string;
  end_time: string;
  timezone: string;
}

export interface WeeklyRule extends WeeklyRuleInput {
  id: string;
}

export interface Blockout {
  id: string;
  starts_at: string;
  ends_at: string;
  reason: string | null;
  created_at: string;
}
