import type { ApiRequestOptions } from "@/lib/api/client";
import type {
  CandidateProfile,
  CandidateProfileInput,
  ResumeMetadata,
} from "@/types/candidate-profile";

export type AuthenticatedRequest = <T>(
  path: string,
  options?: ApiRequestOptions,
) => Promise<T>;

const profilePath = "/v1/users/me/profile";

export function getCandidateProfile(request: AuthenticatedRequest) {
  return request<CandidateProfile>(profilePath);
}

export function getCandidateResume(request: AuthenticatedRequest) {
  return request<ResumeMetadata>("/v1/users/me/resume");
}

export function uploadCandidateResume(
  request: AuthenticatedRequest,
  resume: File,
) {
  const body = new FormData();
  body.append("resume", resume);
  return request<ResumeMetadata>("/v1/users/me/resume", {
    method: "POST",
    body,
  });
}

export function saveCandidateProfile(
  request: AuthenticatedRequest,
  profile: CandidateProfileInput,
) {
  return request<CandidateProfile>(profilePath, {
    method: "PUT",
    body: profile,
  });
}
