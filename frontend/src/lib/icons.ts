import {
  Brain,
  Code,
  Cpu,
  Database,
  Globe,
  Laptop,
  MessageSquare,
  Monitor,
  Rocket,
  Server,
  Smartphone,
  Target,
  Terminal,
  type LucideIcon,
} from "lucide-react";

const iconMap: Record<string, LucideIcon> = {
  Brain,
  Code,
  Cpu,
  Database,
  Globe,
  Laptop,
  MessageSquare,
  Monitor,
  Rocket,
  Server,
  Smartphone,
  Target,
  Terminal,
};

export function getIcon(name: string): LucideIcon {
  return iconMap[name] || Code;
}
