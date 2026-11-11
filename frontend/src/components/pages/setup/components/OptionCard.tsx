import type { LucideIcon } from "lucide-react";

interface OptionCardProps {
  icon: LucideIcon;
  label: string;
  description?: string;
  selected: boolean;
  onClick: () => void;
  layout?: "left" | "center";
}

export function OptionCard({
  icon: Icon,
  label,
  description,
  selected,
  onClick,
  layout = "left",
}: OptionCardProps) {
  const isCenter = layout === "center";

  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`glass rounded-2xl p-5 ${isCenter ? "text-center" : "text-left"} transition-all duration-200 hover:glow-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background ${selected ? "border-primary/60 glow-border bg-primary/10" : ""}`}
    >
      <Icon
        className={`w-6 h-6 mb-3 ${isCenter ? "mx-auto" : ""} ${selected ? "text-primary" : "text-muted-foreground"}`}
      />
      <p className={`font-semibold ${isCenter ? "text-sm" : ""}`}>{label}</p>
      {description && (
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      )}
    </button>
  );
}
