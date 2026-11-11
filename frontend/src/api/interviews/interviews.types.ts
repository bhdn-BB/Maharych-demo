export interface Interview {
  id: string;
  voiceId?: "anna" | "sophia" | "daniel" | "alex" | "";
  userId: number;
  level: string;
  position: string;
  focus: string;
  language?: "uk" | "en";
  scenarioVersion?: number;
  taskId?: string;
  taskTitle: string;
  taskDescription: string;
  status: string;
  startedAt: string;
  endedAt: string | null;
}

export interface StartInterviewParams {
  voiceId?: "anna" | "sophia" | "daniel" | "alex";
  level: string;
  position: string;
  focus: string;
  language?: "uk" | "en";
}

export interface InterviewTopicScore {
  topic_index: number;
  score: number;
  question_type: string;
  comment: string;
  strengths: string[];
  weaknesses: string[];
}

export interface InterviewFeedback {
  score_scale?: number;
  partial?: boolean;
  questions?: {
    question_id: string;
    topic_index: number;
    question: string;
    answer: string;
    score: number | null;
    comment: string;
    clarification: boolean;
    skipped?: boolean;
  }[];
  overall_score: number;
  recommendation: string;
  summary: string;
  topic_scores: InterviewTopicScore[];
  top_strengths: string[];
  top_weaknesses: string[];
}

export interface InterviewList {
  items: Interview[];
  page: number;
  pageSize: number;
  total: number;
}
