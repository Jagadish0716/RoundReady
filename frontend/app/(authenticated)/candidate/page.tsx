import { CandidateBooking } from "@/components/candidate/candidate-booking";
import { CandidateProfileForm } from "@/components/candidate/candidate-profile";
import { SessionWorkspace } from "@/components/interview/session-workspace";
import { NotificationCenter } from "@/components/notifications/notification-center";

export default async function CandidatePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const slot = typeof query.slot === "string" ? query.slot : undefined;
  const interviewer =
    typeof query.interviewer === "string" ? query.interviewer : undefined;
  return (
    <div className="space-y-12">
      <NotificationCenter />
      <CandidateBooking intentSlotId={slot} intentInterviewerId={interviewer} />
      <SessionWorkspace role="candidate" />
      <CandidateProfileForm />
    </div>
  );
}
