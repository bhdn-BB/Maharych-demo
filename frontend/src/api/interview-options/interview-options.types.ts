export interface InterviewOption {
  id: number;
  category: string;
  key: string;
  label: string;
  description?: string;
  icon: string;
  sortOrder: number;
}

export interface InterviewOptions {
  levels: InterviewOption[];
  positions: InterviewOption[];
  focuses: InterviewOption[];
}
