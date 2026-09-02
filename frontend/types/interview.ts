export type SessionStatus =
  | "scheduled"
  | "ready"
  | "in_progress"
  | "completed"
  | "feedback_pending"
  | "feedback_submitted"
  | "candidate_no_show"
  | "interviewer_no_show"
  | "technical_failure"
  | "cancelled";

export interface InterviewSession {
  id: string;
  booking_id: string;
  candidate_id: string;
  interviewer_id: string;
  rubric_id: string;
  scheduled_start: string;
  scheduled_end: string;
  actual_start: string | null;
  actual_end: string | null;
  total_duration_seconds: number;
  status: SessionStatus;
}

export interface RoomAccess {
  token: string;
  expires_at: string;
  join_url: string;
}

export interface RubricCriterion {
  key: string;
  label: string;
  weight: number;
  maximum_score: number;
}

export interface Rubric {
  id: string;
  domain: string;
  topic: string;
  experience_level: string;
  version: number;
  criteria: RubricCriterion[];
  maximum_score: number;
  active: boolean;
}

export type ReadinessLevel =
  "not_ready" | "developing" | "interview_ready" | "strong";
export interface FeedbackInput {
  criterion_scores: Array<{ key: string; score: number }>;
  strengths: string[];
  improvement_areas: string[];
  summary: string;
  readiness_level: ReadinessLevel;
}

export interface FeedbackReport extends FeedbackInput {
  id: string;
  session_id: string;
  total_score: number;
  submitted_at: string;
}
