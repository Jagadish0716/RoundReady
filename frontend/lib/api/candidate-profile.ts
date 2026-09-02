import type { ApiRequestOptions } from "@/lib/api/client";
import type {
  CandidateProfile,
  CandidateProfileInput,
} from "@/types/candidate-profile";

export type AuthenticatedRequest = <T>(
  path: string,
  options?: ApiRequestOptions,
) => Promise<T>;

const profilePath = "/v1/users/me/profile";

export function getCandidateProfile(request: AuthenticatedRequest) {
  return request<CandidateProfile>(profilePath);
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
