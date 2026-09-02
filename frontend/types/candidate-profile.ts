export interface CandidateProfile {
  user_id: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  city: string | null;
  experience_years: string;
  current_role: string | null;
  target_role: string | null;
  preferred_language: string;
  linkedin_url: string | null;
  resume_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface CandidateProfileInput {
  full_name: string;
  phone: string | null;
  email: string | null;
  city: string | null;
  experience_years: string;
  current_role: string | null;
  target_role: string | null;
  preferred_language: string;
  linkedin_url: string | null;
  resume_url: string | null;
}
