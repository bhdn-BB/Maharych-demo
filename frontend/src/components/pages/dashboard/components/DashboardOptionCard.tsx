import { Check, type LucideIcon } from "lucide-react";

interface DashboardOptionCardProps {
  icon: LucideIcon;
  label: string;
  description?: string;
  selected: boolean;
  onClick: () => void;
}

export function DashboardOptionCard({
  icon: Icon,
  label,
  description,
  selected,
  onClick,
}: DashboardOptionCardProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`glass flex items-center gap-3 rounded-2xl p-4 pr-10 text-left transition-colors hover:glow-border w-full h-full group relative focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
        selected ? "border-primary/60 glow-border bg-primary/10" : ""
      }`}
    >
        {selected && (
          <span
            className="absolute top-3 right-3 w-6 h-6 rounded-full bg-primary flex items-center justify-center"
          >
            <Check className="w-3.5 h-3.5 text-primary-foreground" />
          </span>
        )}
      <div className="w-10 h-10 shrink-0 rounded-xl bg-primary/15 flex items-center justify-center group-hover:bg-primary/25 transition-colors">
        <Icon
          className={`w-6 h-6 ${selected ? "text-primary" : "text-muted-foreground group-hover:text-primary transition-colors"}`}
        />
      </div>
      <div><p className="font-display text-lg font-semibold">{label}</p>
      {description && (
        <p className="text-sm text-muted-foreground">{description}</p>
      )}
      </div>
    </button>
  );
}
