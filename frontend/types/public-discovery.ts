import type { InterviewSlot } from "@/types/booking";

export interface PublicInterviewerSkill {
  id: string;
  domain: string;
  topic: string;
  skill_name: string;
  experience_years: string;
}

export interface PublicInterviewer {
  interviewer_id: string;
  headline: string;
  job_title: string | null;
  experience_years: string;
  bio: string | null;
  skills: PublicInterviewerSkill[];
  interview_languages: string[];
  roundready_verified: boolean;
  contact_verified: boolean;
  professional_experience_reviewed: boolean;
  screening_passed: boolean;
  price_paise: number;
  currency: "INR";
}

export type PublicSlot = InterviewSlot;
