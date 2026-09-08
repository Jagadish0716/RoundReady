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
      <CandidateProfileForm />
      <div
        id="notifications"
        className="scroll-mt-6 rounded-xl border border-slate-200 bg-white p-6"
      >
        <NotificationCenter />
      </div>
      <div
        id="book-interview"
        className="scroll-mt-6 rounded-xl border border-slate-200 bg-white p-6"
      >
        <CandidateBooking
          intentSlotId={slot}
          intentInterviewerId={interviewer}
        />
      </div>
      <div
        id="interview-sessions"
        className="scroll-mt-6 rounded-xl border border-slate-200 bg-white p-6"
      >
        <SessionWorkspace role="candidate" />
      </div>
    </div>
  );
}
