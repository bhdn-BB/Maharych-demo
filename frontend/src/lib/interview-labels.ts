const positionLabels: Record<string, string> = {
  frontend: "Frontend",
  backend: "Backend",
  fullstack: "Fullstack",
  devops: "DevOps",
  mobile: "Mobile",
  data: "Data Science",
};

export function positionLabel(key: string): string {
  return positionLabels[key] ?? key;
}

export function interviewTypeLabel(key: string): string {
  const labels: Record<string, string> = {
    algorithms: "Algorithms",
    behavioral: "Behavioral",
    "system-design": "System Design",
  };
  return labels[key] ?? key;
}
