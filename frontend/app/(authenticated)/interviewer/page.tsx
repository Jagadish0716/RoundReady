import { InterviewerWorkspace } from "@/components/interviewer/interviewer-workspace";
import { SessionWorkspace } from "@/components/interview/session-workspace";
import { NotificationCenter } from "@/components/notifications/notification-center";
import { VerificationPanel } from "@/components/interviewer/verification-panel";

export default function InterviewerPage() {
  return (
    <div className="space-y-12">
      <NotificationCenter />
      <SessionWorkspace role="interviewer" />
      <InterviewerWorkspace />
      <VerificationPanel />
    </div>
  );
}
