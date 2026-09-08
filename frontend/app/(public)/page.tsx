import Link from "next/link";
import { PublicDiscovery } from "@/components/public/public-discovery";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="space-y-20">
      <section className="max-w-3xl space-y-5">
        <p className="text-sm font-medium text-neutral-600">
          Human-led technology interviews
        </p>
        <h1 className="text-4xl font-semibold tracking-tight">
          Prepare for your next interview.
        </h1>
        <p className="text-neutral-700">
          RoundReady connects candidates with verified interviewers.
        </p>
        <div className="flex gap-3">
          <Button asChild>
            <Link href="#interviewers">Browse interviewers</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="#interviewers">Find an interview</Link>
          </Button>
        </div>
      </section>
      <PublicDiscovery />
    </div>
  );
}
