"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  BarChart3,
  CircleDollarSign,
  Lightbulb,
  Rocket,
  Star,
  Target,
  UsersRound,
} from "lucide-react";

import { Logo } from "@/components/brand/logo";

const slides = [
  {
    image: "/images/hero/slide1.jpg",
    title: "Better interview preparation.",
    accent: "A brighter you.",
    description:
      "Practice with real tech professionals, get honest feedback, and build the confidence you need for your next opportunity.",
    benefits: [
      {
        icon: UsersRound,
        tone: "emerald",
        title: "Real interviewers",
        text: "Learn from industry professionals",
      },
      {
        icon: BarChart3,
        tone: "blue",
        title: "Practical feedback",
        text: "Understand your strengths and gaps",
      },
      {
        icon: CircleDollarSign,
        tone: "rose",
        title: "Affordable access",
        text: "Just ₹200 per interview",
      },
    ],
    quote:
      "I couldn't crack interviews when I moved from Civil Engineering to IT due to lack of guidance. RoundReady is my way of ensuring others don't go through the same struggle.",
  },
  {
    image: "/images/hero/slide2.jpg",
    title: "Learn from",
    accent: "industry experts.",
    description:
      "Get practical guidance from experienced professionals who have been in your shoes.",
    benefits: [
      {
        icon: Star,
        tone: "emerald",
        title: "Verified professionals",
        text: "Interviewers are thoroughly reviewed",
      },
      {
        icon: UsersRound,
        tone: "blue",
        title: "Real-world experience",
        text: "Learn from people working in top tech roles",
      },
      {
        icon: Lightbulb,
        tone: "amber",
        title: "Personalized feedback",
        text: "Know your strengths and what to improve",
      },
    ],
    quote:
      "Good interview practice gives you clarity, confidence and direction. That's what RoundReady is here to enable.",
  },
  {
    image: "/images/hero/slide3.jpg",
    title: "Affordable practice.",
    accent: "Real career progress.",
    description:
      "High quality interview practice shouldn't be expensive. Get real value at just ₹200 per session.",
    benefits: [
      {
        icon: CircleDollarSign,
        tone: "blue",
        title: "Transparent pricing",
        text: "₹150 to interviewer, ₹50 for platform",
      },
      {
        icon: Target,
        tone: "emerald",
        title: "Focus on your goals",
        text: "Practice the skills that matter",
      },
      {
        icon: Rocket,
        tone: "rose",
        title: "Build your confidence",
        text: "Walk into real interviews prepared",
      },
    ],
    quote:
      "I built RoundReady because I don't want others to face the same lack of guidance and repeated rejections that I did.",
  },
] as const;

const toneClasses = {
  emerald: "bg-emerald-100 text-emerald-700",
  blue: "bg-blue-100 text-blue-700",
  rose: "bg-rose-100 text-rose-600",
  amber: "bg-amber-100 text-amber-600",
};

export function HeroSlider({
  showLogo = false,
  showAction = false,
  className = "",
}: {
  showLogo?: boolean;
  showAction?: boolean;
  className?: string;
}) {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);

  const selectSlide = useCallback((index: number) => setActive(index), []);

  useEffect(() => {
    if (paused) return;
    const timer = window.setInterval(
      () => setActive((current) => (current + 1) % slides.length),
      5000,
    );
    return () => window.clearInterval(timer);
  }, [paused, active]);

  return (
    <section
      aria-roledescription="carousel"
      aria-label="Why candidates choose RoundReady"
      tabIndex={0}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget))
          setPaused(false);
      }}
      onKeyDown={(event) => {
        if (event.key === "ArrowRight") {
          event.preventDefault();
          selectSlide((active + 1) % slides.length);
        }
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          selectSlide((active - 1 + slides.length) % slides.length);
        }
      }}
      className={`relative isolate h-full min-h-[690px] overflow-hidden rounded-[1.75rem] border border-blue-100 bg-blue-50 shadow-[0_24px_70px_-48px_rgba(30,64,175,0.55)] outline-none focus-visible:ring-2 focus-visible:ring-blue-600 md:min-h-[720px] ${className}`}
    >
      {slides.map((slide, index) => (
        <div
          key={slide.title}
          aria-hidden={index !== active}
          className={`absolute inset-0 transition-opacity duration-700 motion-reduce:transition-none ${index === active ? "z-0 opacity-100" : "pointer-events-none -z-10 opacity-0"}`}
        >
          <div
            className="absolute inset-0 bg-cover bg-[center_bottom]"
            style={{ backgroundImage: `url('${slide.image}')` }}
          />
          <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.99)_0%,rgba(255,255,255,0.95)_35%,rgba(248,251,255,0.64)_58%,rgba(238,246,255,0.06)_84%),linear-gradient(180deg,rgba(255,255,255,0.76)_0%,rgba(255,255,255,0.10)_48%,rgba(15,35,75,0.10)_100%)]" />
        </div>
      ))}

      <div className="relative z-10 flex min-h-[690px] max-w-[650px] flex-col p-8 sm:p-10 md:min-h-[720px] xl:p-12">
        {showLogo ? (
          <div>
            <Link
              href="/"
              aria-label="RoundReady home"
              className="inline-flex rounded-md focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
            >
              <Logo variant="horizontal" priority className="w-[210px]" />
            </Link>
            <p className="mt-1 text-xs font-medium tracking-wide text-slate-600">
              Practice Today. Perform Tomorrow.
            </p>
          </div>
        ) : null}

        <div
          className={showLogo ? "mt-11" : "mt-2"}
          aria-live="polite"
          aria-atomic="true"
        >
          <p className="sr-only">
            Slide {active + 1} of {slides.length}
          </p>
          <h1 className="text-[2.75rem] leading-[1.04] font-bold tracking-[-0.04em] text-slate-950 xl:text-5xl">
            {slides[active].title}{" "}
            <span className="text-blue-600">{slides[active].accent}</span>
          </h1>
          <p className="mt-4 max-w-[540px] text-base leading-7 text-slate-700 xl:text-lg">
            {slides[active].description}
          </p>
          {showAction ? (
            <Link
              href="#interviewers"
              className="mt-5 inline-flex h-11 items-center rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 hover:bg-blue-700 hover:no-underline"
            >
              Browse interviewers
            </Link>
          ) : null}
        </div>

        <div className="mt-6 grid gap-4">
          {slides[active].benefits.map((benefit) => {
            const Icon = benefit.icon;
            return (
              <div key={benefit.title} className="flex items-center gap-4">
                <span
                  className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${toneClasses[benefit.tone]}`}
                >
                  <Icon className="h-5 w-5" aria-hidden />
                </span>
                <div>
                  <h2 className="font-semibold text-slate-950">
                    {benefit.title}
                  </h2>
                  <p className="mt-0.5 text-sm text-slate-600">
                    {benefit.text}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        <blockquote className="mt-auto mb-8 max-w-[440px] rounded-2xl border border-white/90 bg-white/86 p-5 shadow-[0_18px_45px_-28px_rgba(15,23,42,0.45)] backdrop-blur-md">
          <p className="text-sm leading-6 text-slate-700">
            “{slides[active].quote}”
          </p>
          <footer className="mt-3 text-sm">
            <span className="block font-semibold text-slate-950">
              — Jagadish
            </span>
            <span className="mt-0.5 block text-slate-600">
              Founder, RoundReady
            </span>
          </footer>
        </blockquote>

        <div
          className="absolute bottom-6 left-8 flex gap-2 sm:left-10 xl:left-12"
          role="group"
          aria-label="Choose hero slide"
        >
          {slides.map((slide, index) => (
            <button
              key={slide.title}
              type="button"
              aria-label={`Show slide ${index + 1}: ${slide.title} ${slide.accent}`}
              aria-current={index === active ? "true" : undefined}
              onClick={() => selectSlide(index)}
              className={`h-2 rounded-full transition-all focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 focus-visible:outline-none ${index === active ? "w-8 bg-blue-600" : "w-6 bg-slate-300 hover:bg-slate-400"}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
