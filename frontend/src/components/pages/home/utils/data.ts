import {
  Brain,
  Code,
  Cpu,
  Database,
  Globe,
  Laptop,
  Monitor,
  Rocket,
  Server,
  Smartphone,
  Sparkles,
  Users,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface LevelItem {
  title: string;
  desc: string;
  icon: LucideIcon;
  delay: number;
}

export interface PositionItem {
  label: string;
  icon: LucideIcon;
}

export interface StepItem {
  num: string;
  title: string;
  desc: string;
  icon: LucideIcon;
}

export const levels: LevelItem[] = [
  {
    title: "Junior",
    desc: "Entry-level questions & fundamentals",
    icon: Rocket,
    delay: 0,
  },
  {
    title: "Middle",
    desc: "Intermediate patterns & problem solving",
    icon: Code,
    delay: 0.1,
  },
  {
    title: "Senior",
    desc: "Architecture, leadership & depth",
    icon: Brain,
    delay: 0.2,
  },
  {
    title: "Lead",
    desc: "System design & strategic thinking",
    icon: Cpu,
    delay: 0.3,
  },
];

export const positions: PositionItem[] = [
  { label: "Frontend", icon: Monitor },
  { label: "Backend", icon: Server },
  { label: "Fullstack", icon: Laptop },
  { label: "DevOps", icon: Globe },
  { label: "Mobile", icon: Smartphone },
  { label: "Data Science", icon: Database },
];

export const steps: StepItem[] = [
  {
    num: "01",
    title: "Choose Settings",
    desc: "Pick your level, position & focus area",
    icon: Sparkles,
  },
  {
    num: "02",
    title: "Start Interview",
    desc: "Face realistic AI-powered questions",
    icon: Zap,
  },
  {
    num: "03",
    title: "Get Feedback",
    desc: "Receive detailed performance analysis",
    icon: Users,
  },
];
