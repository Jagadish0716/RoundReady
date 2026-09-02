import type { VerificationStatus } from "@/types/interviewer";

const descriptions: Record<VerificationStatus, string> = {
  pending:
    "Complete your professional profile before submitting it for review.",
  under_review: "Your profile is being reviewed by the RoundReady team.",
  verified: "Your interviewer profile is verified.",
  rejected: "Your verification was not approved. Review the reason below.",
  suspended: "Your interviewer access is currently suspended.",
};

export function VerificationStatusCard({
  status,
  reason,
}: {
  status: VerificationStatus;
  reason: string | null;
}) {
  return (
    <section
      className="rounded-lg border border-neutral-200 bg-white p-4"
      aria-label="Verification status"
    >
      <p className="text-xs font-semibold tracking-wide text-neutral-500 uppercase">
        Verification
      </p>
      <p className="mt-1 text-lg font-semibold">
        {status.replace("_", " ").toUpperCase()}
      </p>
      <p className="mt-1 text-sm text-neutral-600">{descriptions[status]}</p>
      {reason ? (
        <p className="mt-2 text-sm text-red-700">Reason: {reason}</p>
      ) : null}
    </section>
  );
}
