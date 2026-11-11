import { Languages } from "lucide-react";
import { OptionCard } from "./OptionCard";

type Language = "" | "uk" | "en";

export function LanguageStep({ selected, onSelect }: { selected: Language; onSelect: (value: Language) => void }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <OptionCard icon={Languages} label="Українська" description="Questions and feedback in Ukrainian" selected={selected === "uk"} onClick={() => onSelect("uk")} />
      <OptionCard icon={Languages} label="English" description="Questions and feedback in English" selected={selected === "en"} onClick={() => onSelect("en")} />
    </div>
  );
}
