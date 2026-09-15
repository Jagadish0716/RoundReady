import Link from "next/link";
import { FounderPhoto } from "@/components/public/founder-photo";
import { PublicDiscovery } from "@/components/public/public-discovery";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="space-y-20">
      <section className="grid gap-10 py-8 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-center">
        <div className="max-w-3xl space-y-6">
          <p className="text-sm font-medium text-neutral-600">
            Human-led technology interview practice
          </p>
          <div className="space-y-4">
            <h1 className="text-4xl font-semibold tracking-tight text-neutral-950 md:text-5xl">
              Practice interviews with real tech professionals.
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-neutral-700">
              RoundReady helps candidates preparing for real interviews book
              affordable ₹200 practice sessions with verified interviewers and
              receive practical feedback from people working in technology.
            </p>
          </div>
          <p className="text-sm font-medium text-blue-700">
            Explore freely. Sign in when you&apos;re ready to book.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link href="#interviewers">Browse interviewers</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/register?role=interviewer">
                Become an interviewer
              </Link>
            </Button>
          </div>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-semibold text-neutral-950">
            One interview. ₹200.
          </p>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            Book practice when you need it. No expensive packages or
            subscription required.
          </p>
          <dl className="mt-5 grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-neutral-50 p-4">
              <dt className="text-xs font-medium text-neutral-500">
                Interviewer
              </dt>
              <dd className="mt-1 text-2xl font-semibold">₹150</dd>
            </div>
            <div className="rounded-lg bg-neutral-50 p-4">
              <dt className="text-xs font-medium text-neutral-500">Platform</dt>
              <dd className="mt-1 text-2xl font-semibold">₹50</dd>
            </div>
          </dl>
        </div>
      </section>

      <section
        className="grid gap-5 md:grid-cols-3"
        aria-label="How RoundReady works"
      >
        {[
          [
            "Browse verified interviewers",
            "Compare experience, domains, languages, price, and next availability without creating an account.",
          ],
          [
            "Choose a slot",
            "Open a profile when you want more context, then pick an available ₹200 interview slot.",
          ],
          [
            "Practice and improve",
            "Meet a real technology professional, answer practical questions, and use the feedback to prepare better.",
          ],
        ].map(([title, copy]) => (
          <div key={title} className="rounded-lg border bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-neutral-950">
              {title}
            </h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">{copy}</p>
          </div>
        ))}
      </section>

      <PublicDiscovery />

      <section
        id="pricing"
        className="grid gap-8 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm md:grid-cols-[0.9fr_1.1fr] md:p-8"
        aria-labelledby="pricing-heading"
      >
        <div>
          <p className="text-sm font-semibold text-blue-700">
            Transparent pricing
          </p>
          <h2 id="pricing-heading" className="mt-2 text-3xl font-semibold">
            One interview. ₹200.
          </h2>
          <p className="mt-3 text-neutral-700">
            RoundReady is meant to be useful interview practice, not an
            expensive preparation package.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg bg-neutral-50 p-5">
            <p className="text-sm text-neutral-600">Paid to your interviewer</p>
            <p className="mt-2 text-3xl font-semibold">₹150</p>
          </div>
          <div className="rounded-lg bg-neutral-50 p-5">
            <p className="text-sm text-neutral-600">Helps us run RoundReady</p>
            <p className="mt-2 text-3xl font-semibold">₹50</p>
          </div>
          <p className="text-sm leading-6 text-neutral-600 sm:col-span-2">
            No subscription required. Book practice when you need it.
          </p>
        </div>
      </section>

      <section
        id="founder"
        className="grid gap-8 md:grid-cols-[minmax(0,18rem)_minmax(0,1fr)] md:items-center"
        aria-labelledby="founder-heading"
      >
        <FounderPhoto />
        <div className="space-y-4">
          <p className="text-sm font-semibold text-blue-700">Founder story</p>
          <h2 id="founder-heading" className="text-3xl font-semibold">
            Why I built RoundReady
          </h2>
          <div className="space-y-4 leading-7 text-neutral-700">
            <p>
              I&apos;m from a Civil Engineering background. When I decided to
              move into IT, I did not have proper guidance about what to learn,
              which skills companies expected, or how technical interviews
              actually worked.
            </p>
            <p>
              I failed several interviews while trying to figure those things
              out by myself. That experience is one of the main reasons I built
              RoundReady.
            </p>
            <p>
              I do not want other candidates to walk into interviews without
              knowing whether they are really prepared. RoundReady gives
              candidates an affordable way to practice with real technology
              professionals, understand where they need to improve, and get
              practical guidance before the interview that matters.
            </p>
            <p>
              My goal is simple: make useful interview guidance accessible to
              people who are serious about improving their careers.
            </p>
          </div>
        </div>
      </section>

      <section className="space-y-5 rounded-lg bg-neutral-950 p-6 text-white md:p-8">
        <h2 className="text-3xl font-semibold">
          Ready to practice with a real interviewer?
        </h2>
        <p className="max-w-2xl text-neutral-200">
          Browse verified technology professionals, open the profiles that fit
          your preparation needs, and sign in only when you are ready to book.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href="#interviewers">Browse interviewers</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/register?role=interviewer">Become an interviewer</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
