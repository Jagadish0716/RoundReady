import Link from "next/link";
import { SessionWorkspace } from "@/components/interview/session-workspace";

export default function CandidateBookingsPage() {
  return (
    <div className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">My bookings</h1>
          <p className="mt-1 text-sm text-slate-600">
            Open your supported interview sessions and their current status.
          </p>
        </div>
        <Link
          href="/candidate/interviews"
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Browse interviewers
        </Link>
      </header>
      <SessionWorkspace role="candidate" />
    </div>
  );
}
