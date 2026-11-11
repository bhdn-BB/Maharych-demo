import Link from "next/link";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowDown,
  ArrowRight,
  AudioLines,
  Check,
  MessageCircle,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface HeroSectionProps {
  isAuthed: boolean;
}

const samples = {
  Behavioral:
    "Tell me about a time you received feedback you disagreed with. How did you respond, and what happened next?",
  Algorithms:
    "Given a list of numbers, how would you find the first duplicate? Explain your approach and its time and space complexity.",
  "System Design":
    "How would you design a notification service for 100,000 users, and what would you do if traffic doubled?",
};

export function HeroSection({ isAuthed }: HeroSectionProps) {
  const [sample, setSample] = useState<keyof typeof samples>("Behavioral");

  return (
    <section className="relative px-6 pb-20 pt-32 lg:pb-28 lg:pt-40">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-0 h-[500px] w-[min(90vw,700px)] -translate-x-1/2 rounded-full bg-primary/10 blur-[120px]"
      />
      <div className="container relative mx-auto grid max-w-6xl items-center gap-14 lg:grid-cols-[1fr_0.95fr] lg:gap-20">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary">
            <Sparkles aria-hidden="true" className="h-3.5 w-3.5" />
            Your space to practice
          </div>
          <h1 className="mt-6 max-w-2xl font-display text-5xl font-bold leading-[1.08] tracking-tight sm:text-6xl xl:text-7xl">
            Get ready for your{" "}
            <span className="gradient-text">next interview.</span>
          </h1>
          <p className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Practice out loud with an AI interviewer, explore questions for your
            role, and learn from your feedback.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button
              asChild
              size="lg"
              className="glow-button h-12 rounded-xl px-6 font-semibold"
            >
              <Link href={isAuthed ? "/dashboard" : "/register"}>
                {isAuthed ? "Choose an interview" : "Get started"}
                <ArrowRight aria-hidden="true" className="h-4 w-4" />
              </Link>
            </Button>
            <a
              href="#explore"
              className="inline-flex h-12 items-center gap-2 rounded-xl px-4 text-sm font-medium text-foreground/80 transition hover:bg-white/5 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              Explore questions{" "}
              <ArrowDown aria-hidden="true" className="h-4 w-4" />
            </a>
          </div>
          <div className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground">
            {[
              "Voice practice",
              "Your choice of language",
              "Personal feedback",
            ].map((item) => (
              <span key={item} className="inline-flex items-center gap-1.5">
                <Check
                  aria-hidden="true"
                  className="h-3.5 w-3.5 text-primary"
                />
                {item}
              </span>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="glass glow-border rounded-[28px] p-4 sm:p-6"
        >
          <div className="flex items-center justify-between gap-3 border-b border-border/40 pb-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/15 text-primary">
                <AudioLines aria-hidden="true" className="h-5 w-5" />
              </div>
              <div>
                <p className="font-display text-sm font-semibold">
                  A little practice
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Explore a sample question
                </p>
              </div>
            </div>
            <span className="rounded-full border border-primary/20 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider text-primary">
              Preview
            </span>
          </div>
          <div
            className="mt-5 flex flex-wrap gap-2"
            aria-label="Sample interview type"
          >
            {(Object.keys(samples) as (keyof typeof samples)[]).map((type) => (
              <button
                key={type}
                type="button"
                aria-pressed={sample === type}
                onClick={() => setSample(type)}
                className={`rounded-full border px-3 py-2 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${sample === type ? "border-primary/60 bg-primary/20 text-foreground" : "border-border/50 text-muted-foreground hover:border-primary/40 hover:text-foreground"}`}
              >
                {type}
              </button>
            ))}
          </div>
          <div
            className="mt-5 min-h-[150px] rounded-2xl border border-primary/15 bg-background/50 p-5"
            aria-live="polite"
            aria-atomic="true"
          >
            <div className="flex items-center gap-2 text-xs font-medium text-primary">
              <MessageCircle aria-hidden="true" className="h-4 w-4" /> Your
              interviewer
            </div>
            <p className="mt-4 font-display text-lg leading-relaxed text-foreground sm:text-xl">
              “{samples[sample]}”
            </p>
          </div>
          <div className="mt-4 flex items-center gap-3 rounded-xl bg-white/[0.03] px-4 py-3">
            <AudioLines
              aria-hidden="true"
              className="h-5 w-5 shrink-0 text-primary"
            />
            <p className="text-xs leading-relaxed text-muted-foreground">
              In your interview, listen to each question and answer in your own
              words.
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
