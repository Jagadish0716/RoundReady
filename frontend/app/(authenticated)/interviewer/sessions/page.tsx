import { SessionWorkspace } from "@/components/interview/session-workspace";
export default function Page() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <SessionWorkspace role="interviewer" />
    </div>
  );
}
