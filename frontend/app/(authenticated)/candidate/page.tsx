import Link from "next/link";
import { CandidateBooking } from "@/components/candidate/candidate-booking";

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
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Candidate dashboard
        </h1>
        <p className="mt-1 text-slate-600">
          Manage your profile, find an interviewer, and keep track of your
          interviews.
        </p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          [
            "Complete your profile",
            "/candidate/profile",
            "Keep your experience and resume current.",
          ],
          [
            "Browse interviewers",
            "/candidate/interviews",
            "Explore verified interviewers and available slots.",
          ],
          [
            "My bookings",
            "/candidate/bookings",
            "Open your existing interview sessions.",
          ],
          [
            "Notifications",
            "/candidate/notifications",
            "Review your RoundReady updates.",
          ],
        ].map(([title, href, description]) => (
          <Link
            key={href}
            href={href}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:shadow"
          >
            <h2 className="font-semibold text-slate-950">{title}</h2>
            <p className="mt-2 text-sm text-slate-600">{description}</p>
          </Link>
        ))}
      </div>
      {slot && interviewer ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <CandidateBooking
            intentSlotId={slot}
            intentInterviewerId={interviewer}
          />
        </div>
      ) : null}
    </div>
  );
}
