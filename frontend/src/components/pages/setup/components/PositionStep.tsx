import { getIcon } from "@/lib/icons";
import { OptionCard } from "./OptionCard";
import type { InterviewOptions } from "@/api/interview-options/interview-options.types";

interface PositionStepProps {
  positions: InterviewOptions["positions"];
  selected: string;
  onSelect: (key: string) => void;
}

export function PositionStep({
  positions,
  selected,
  onSelect,
}: PositionStepProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {positions.map((p) => {
        const Icon = getIcon(p.icon);
        return (
          <OptionCard
            key={p.key}
            icon={Icon}
            label={p.label}
            selected={selected === p.key}
            onClick={() => onSelect(p.key)}
            layout="center"
          />
        );
      })}
    </div>
  );
}
