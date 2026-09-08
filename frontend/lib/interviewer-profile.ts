import type {
  InterviewerProfile,
  InterviewerProfileInput,
} from "@/types/interviewer";

export type InterviewerProfileField = keyof InterviewerProfileInput;
export type InterviewerProfileErrors = Partial<
  Record<InterviewerProfileField, string>
>;

const linkedinProfile =
  /^https:\/\/(?:www\.)?linkedin\.com\/in\/[^/?#]+\/?(?:[?#].*)?$/i;
const githubProfile =
  /^https:\/\/(?:www\.)?github\.com\/[^/?#]+\/?(?:[?#].*)?$/i;

export function validateInterviewerProfile(
  profile: InterviewerProfileInput | InterviewerProfile,
): InterviewerProfileErrors {
  const errors: InterviewerProfileErrors = {};
  const name = profile.full_name?.trim() ?? "";
  if (name.length < 2) errors.full_name = "Full name is required.";
  else if (name.length > 100)
    errors.full_name = "Full name must be at most 100 characters.";
  if (!profile.headline.trim()) errors.headline = "Headline is required.";
  if (!profile.company?.trim()) errors.company = "Company is required.";
  if (!profile.job_title?.trim()) errors.job_title = "Job title is required.";
  if (
    !/^\d{1,2}(?:\.\d)?$/.test(profile.experience_years) ||
    Number(profile.experience_years) > 60
  )
    errors.experience_years = "Experience must be between 0 and 60 years.";
  if (!profile.linkedin_url?.trim())
    errors.linkedin_url = "LinkedIn URL is required.";
  else if (!linkedinProfile.test(profile.linkedin_url.trim()))
    errors.linkedin_url = "Enter a valid LinkedIn profile URL.";
  if (!profile.github_url?.trim())
    errors.github_url = "GitHub URL is required.";
  else if (!githubProfile.test(profile.github_url.trim()))
    errors.github_url = "Enter a valid GitHub profile URL.";
  const bio = profile.bio?.trim() ?? "";
  if (!bio) errors.bio = "Bio is required.";
  else if (bio.length < 50) errors.bio = "Bio must be at least 50 characters.";
  else if (bio.length > 4000)
    errors.bio = "Bio must be at most 4000 characters.";
  return errors;
}

export function isInterviewerProfileComplete(
  profile: InterviewerProfileInput | InterviewerProfile | null,
): boolean {
  return Boolean(
    profile && Object.keys(validateInterviewerProfile(profile)).length === 0,
  );
}
