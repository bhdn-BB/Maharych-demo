import type { InterviewOption } from "@/api/interview-options/interview-options.types";
import { getIcon } from "@/lib/icons";
import { DashboardOptionCard } from "./DashboardOptionCard";

interface CategorySectionProps {
  title: string;
  highlight: string;
  subtitle: string;
  items: InterviewOption[];
  selectedKey: string;
  onSelect: (key: string) => void;
}

export function CategorySection({
  title,
  highlight,
  subtitle,
  items,
  selectedKey,
  onSelect,
}: CategorySectionProps) {
  if (items.length === 0) return null;

  const parts = title.split(highlight);

  return (
    <section className="py-6 px-6">
      <div className="mx-auto max-w-5xl">
        <div className="mb-5">
          <h2
            className="font-display text-2xl md:text-3xl font-bold"
          >
            {parts[0]}
            <span className="gradient-text">{highlight}</span>
            {parts[1]}
          </h2>
          <p
            className="mt-2 text-muted-foreground"
          >
            {subtitle}
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {items.map((item) => (
              <DashboardOptionCard
                key={item.key}
                icon={getIcon(item.icon)}
                label={item.label}
                description={item.description}
                selected={selectedKey === item.key}
                onClick={() => onSelect(item.key)}
              />
          ))}
        </div>
      </div>
    </section>
  );
}
