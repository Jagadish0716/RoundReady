import { CandidateBooking } from "@/components/candidate/candidate-booking";
import { CandidateProfileForm } from "@/components/candidate/candidate-profile";
import { SessionWorkspace } from "@/components/interview/session-workspace";
import { NotificationCenter } from "@/components/notifications/notification-center";

export default function CandidatePage() {
  return (
    <div className="space-y-12">
      <NotificationCenter />
      <CandidateBooking />
      <SessionWorkspace role="candidate" />
      <CandidateProfileForm />
    </div>
  );
}
