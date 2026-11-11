import type { InterviewOptions } from "@/api/interview-options/interview-options.types";

export interface SetupFormProps {
  options: InterviewOptions;
}

export interface SetupSelection {
  level: string;
  position: string;
  focus: string;
}
