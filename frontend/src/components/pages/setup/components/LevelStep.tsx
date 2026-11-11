import { getIcon } from "@/lib/icons";
import { OptionCard } from "./OptionCard";
import type { InterviewOptions } from "@/api/interview-options/interview-options.types";

interface LevelStepProps {
  levels: InterviewOptions["levels"];
  selected: string;
  onSelect: (key: string) => void;
}

export function LevelStep({ levels, selected, onSelect }: LevelStepProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {levels.map((l) => {
        const Icon = getIcon(l.icon);
        return (
          <OptionCard
            key={l.key}
            icon={Icon}
            label={l.label}
            description={l.description}
            selected={selected === l.key}
            onClick={() => onSelect(l.key)}
          />
        );
      })}
    </div>
  );
}
