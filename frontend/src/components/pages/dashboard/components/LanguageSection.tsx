import { Languages } from "lucide-react";
import { DashboardOptionCard } from "./DashboardOptionCard";

type Language = "" | "uk" | "en";

export function LanguageSection({ selected, onSelect }: { selected: Language; onSelect: (value: Language) => void }) {
  return (
    <section className="px-6 py-6" aria-labelledby="interview-language-heading">
      <div className="mx-auto max-w-5xl">
        <h2 id="interview-language-heading" className="font-display text-2xl font-bold md:text-3xl">
          Interview <span className="gradient-text">Language</span>
        </h2>
        <p className="mt-2 text-muted-foreground">Choose the language for the questions, audio and feedback.</p>
        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <DashboardOptionCard icon={Languages} label="Українська" description="Questions and feedback in Ukrainian" selected={selected === "uk"} onClick={() => onSelect("uk")} />
          <DashboardOptionCard icon={Languages} label="English" description="Questions and feedback in English" selected={selected === "en"} onClick={() => onSelect("en")} />
        </div>
      </div>
    </section>
  );
}
