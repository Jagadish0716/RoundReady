import Link from "next/link";
import {
  ArrowRight,
  CalendarDays,
  MessageSquareText,
  Search,
} from "lucide-react";
import { FounderPhoto } from "@/components/public/founder-photo";
import { HeroSlider } from "@/components/public/hero-slider";
import { PublicDiscovery } from "@/components/public/public-discovery";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="space-y-24 pb-6 sm:space-y-28">
      <HeroSlider showAction className="min-h-[680px] md:min-h-[720px]" />

      <section id="how-it-works" aria-labelledby="workflow-heading">
        <SectionHeading
          eyebrow="Simple by design"
          title="How RoundReady works"
          copy="Go from searching to useful interview feedback in three clear steps."
        />
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {[
            {
              number: "01",
              icon: <Search aria-hidden />,
              title: "Find your interviewer",
              copy: "Browse verified technology professionals by expertise.",
            },
            {
              number: "02",
              icon: <CalendarDays aria-hidden />,
              title: "Choose a time",
              copy: "Select an available interview slot that works for you.",
            },
            {
              number: "03",
              icon: <MessageSquareText aria-hidden />,
              title: "Practice & improve",
              copy: "Attend your mock interview and receive practical feedback.",
            },
          ].map((item) => (
            <article
              key={item.number}
              className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_18px_50px_-38px_rgba(15,23,42,0.45)] transition duration-200 hover:-translate-y-1 hover:border-blue-200 hover:shadow-[0_22px_55px_-35px_rgba(37,99,235,0.4)]"
            >
              <span className="absolute top-3 right-5 text-5xl font-black text-slate-100">
                {item.number}
              </span>
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-700 [&>svg]:h-5 [&>svg]:w-5">
                {item.icon}
              </span>
              <h3 className="mt-6 text-lg font-bold text-slate-950">
                {item.title}
              </h3>
              <p className="mt-2 leading-7 text-slate-600">{item.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <PublicDiscovery />

      <section
        id="pricing"
        className="relative overflow-hidden rounded-[2rem] bg-slate-950 px-6 py-10 text-white shadow-xl sm:px-10 lg:px-14"
        aria-labelledby="pricing-heading"
      >
        <div className="absolute -top-28 right-0 h-72 w-72 rounded-full bg-blue-600/25 blur-3xl" />
        <div className="relative grid gap-9 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <div>
            <p className="text-sm font-bold tracking-wider text-blue-300 uppercase">
              Transparent from the start
            </p>
            <h2
              id="pricing-heading"
              className="mt-3 text-3xl font-bold sm:text-4xl"
            >
              ₹200{" "}
              <span className="text-xl font-medium text-slate-300">
                per mock interview
              </span>
            </h2>
            <p className="mt-4 max-w-lg leading-7 text-slate-300">
              No subscription. No expensive package. Book one focused practice
              session whenever you need it.
            </p>
          </div>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/7 p-6">
              <dt className="text-sm text-slate-300">
                Goes to the interviewer
              </dt>
              <dd className="mt-2 text-4xl font-bold">₹150</dd>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/7 p-6">
              <dt className="text-sm text-slate-300">Helps run RoundReady</dt>
              <dd className="mt-2 text-4xl font-bold">₹50</dd>
            </div>
          </dl>
        </div>
      </section>

      <section
        id="why-roundready"
        className="grid gap-8 rounded-[2rem] border border-blue-100 bg-blue-50/65 p-6 sm:p-9 lg:grid-cols-[minmax(240px,0.7fr)_minmax(0,1.3fr)] lg:items-center lg:p-12"
        aria-labelledby="founder-heading"
      >
        <FounderPhoto />
        <div>
          <p className="text-sm font-bold tracking-wider text-blue-700 uppercase">
            A note from the founder
          </p>
          <h2
            id="founder-heading"
            className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl"
          >
            Why I built RoundReady
          </h2>
          <div className="mt-5 space-y-4 leading-7 text-slate-700">
            <p>
              I&apos;m from a Civil Engineering background. When I decided to
              move into IT, I didn&apos;t have proper guidance about what to
              learn, which skills companies expected, or how technical
              interviews actually worked.
            </p>
            <p>
              I failed several interviews while trying to figure these things
              out myself. That&apos;s one of the main reasons I built
              RoundReady. I don&apos;t want other candidates to walk into
              interviews without knowing whether they&apos;re really prepared.
            </p>
            <p>
              RoundReady gives candidates an affordable way to practice with
              real technology professionals, identify gaps, and get practical
              guidance before the interview that actually matters.
            </p>
          </div>
          <div className="mt-7 inline-flex flex-wrap items-center gap-x-5 gap-y-2 rounded-2xl border border-blue-200 bg-white px-5 py-4 shadow-sm">
            <strong className="text-xl text-blue-700">
              ₹200 per interview
            </strong>
            <span className="text-sm font-medium text-slate-600">
              ₹150 → interviewer
            </span>
            <span className="text-sm font-medium text-slate-600">
              ₹50 → running RoundReady
            </span>
          </div>
        </div>
      </section>

      <section className="relative overflow-hidden rounded-[2rem] bg-blue-600 px-6 py-12 text-center text-white shadow-xl shadow-blue-900/15 sm:px-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.2),transparent_35%)]" />
        <div className="relative mx-auto max-w-3xl">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Ready to practice before the real interview?
          </h2>
          <p className="mt-3 text-lg text-blue-100">
            Practice with someone who has been there.
          </p>
          <Button
            asChild
            className="mt-7 h-12 rounded-xl bg-white px-6 text-blue-700 hover:bg-blue-50"
          >
            <Link href="#interviewers">
              Browse interviewers{" "}
              <ArrowRight className="ml-2 h-4 w-4" aria-hidden />
            </Link>
          </Button>
          <p className="mt-3 text-sm text-blue-100">
            Browse freely. No forced signup.
          </p>
        </div>
      </section>
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  copy,
}: {
  eyebrow: string;
  title: string;
  copy: string;
}) {
  return (
    <header className="max-w-2xl">
      <p className="text-sm font-bold tracking-wider text-blue-700 uppercase">
        {eyebrow}
      </p>
      <h2
        id="workflow-heading"
        className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl"
      >
        {title}
      </h2>
      <p className="mt-3 text-lg leading-7 text-slate-600">{copy}</p>
    </header>
  );
}
