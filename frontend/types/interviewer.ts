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

export interface InterviewerProfileInput {
  headline: string;
  company: string | null;
  job_title: string | null;
  experience_years: string;
  linkedin_url: string | null;
  github_url: string | null;
  bio: string | null;
}

export interface InterviewerProfile extends InterviewerProfileInput {
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
