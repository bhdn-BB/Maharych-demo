"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { MessageCircle, Sparkles } from "lucide-react";
import { HeroSection } from "./components/HeroSection";
import { LevelsSection } from "./components/LevelsSection";
import { PositionsSection } from "./components/PositionsSection";
import { StepsSection } from "./components/StepsSection";

export function HomePage() {
  const { data: session } = useSession();
  const isAuthed = !!session?.user;
  const [level, setLevel] = useState("Junior");
  const [position, setPosition] = useState("Frontend");

  const topics: Record<string, string> = {
    Frontend: "a product page that takes five seconds to become interactive on mobile",
    Backend: "an API endpoint whose response time rises from 200 ms to 3 seconds under load",
    Fullstack: "an online shop where users sometimes see stale stock after checkout",
    DevOps: "a deployment that intermittently causes a few minutes of downtime",
    Mobile: "a mobile app that must save changes while the user is offline",
    "Data Science": "a fraud detection model whose precision dropped from 90% to 60% after deployment",
  };
  const prompts: Record<string, string> = {
    Junior: "What would you check first, and what evidence would you look for?",
    Middle: "How would you investigate the cause and verify your proposed fix?",
    Senior:
      "How would you diagnose it, prioritize improvements, and explain the trade-offs?",
    Lead: "How would you coordinate the team, prioritize work, and measure the outcome?",
  };

  return (
    <div className="min-h-screen gradient-bg overflow-hidden">
      <HeroSection isAuthed={isAuthed} />
      <div id="explore" className="scroll-mt-20">
        <LevelsSection selected={level} onSelect={setLevel} />
        <PositionsSection selected={position} onSelect={setPosition} />
        <section
          className="px-6 pb-24"
          aria-labelledby="sample-question-heading"
        >
          <div className="glass glow-border mx-auto max-w-3xl rounded-2xl p-6 sm:p-8">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-primary">
              <Sparkles aria-hidden="true" className="h-4 w-4" />
              Try a sample
            </div>
            <h2
              id="sample-question-heading"
              className="mt-3 font-display text-2xl font-semibold"
            >
              See what a question could look like
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Choose a level and position above to explore an example.
            </p>
            <div
              className="mt-6 rounded-xl border border-primary/20 bg-primary/5 p-5"
              aria-live="polite"
              aria-atomic="true"
            >
              <div className="flex items-center gap-2 text-xs font-medium text-primary">
                <MessageCircle aria-hidden="true" className="h-4 w-4" />
                {level} · {position}
              </div>
              <p className="mt-3 text-base leading-relaxed text-foreground">
                Imagine {topics[position]}. {prompts[level]}
              </p>
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              This is a preview. You can choose your interview settings when you
              start.
            </p>
          </div>
        </section>
      </div>
      <StepsSection />
    </div>
  );
}
