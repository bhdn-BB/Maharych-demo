import { getIcon } from "@/lib/icons";
import { OptionCard } from "./OptionCard";
import type { InterviewOptions } from "@/api/interview-options/interview-options.types";

interface FocusStepProps {
  focuses: InterviewOptions["focuses"];
  selected: string;
  onSelect: (key: string) => void;
}

export function FocusStep({ focuses, selected, onSelect }: FocusStepProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {focuses.map((f) => {
        const Icon = getIcon(f.icon);
        return (
          <OptionCard
            key={f.key}
            icon={Icon}
            label={f.label}
            description={f.description}
            selected={selected === f.key}
            onClick={() => onSelect(f.key)}
          />
        );
      })}
    </div>
  );
}
