import { apiFetch } from "@/lib/fetch";
import type { InterviewOptions } from "./interview-options.types";
import { isSupportedInterviewFocus } from "@/lib/interview-focus";

export const interviewOptionsApi = {
  getAll: async (): Promise<InterviewOptions> => {
    const res = await apiFetch("/interview-options", {
      next: { revalidate: 3600 },
    } as RequestInit);

    if (!res.ok) {
      throw new Error("Failed to fetch interview options");
    }

    const options: InterviewOptions = await res.json();
    return {
      ...options,
      focuses: options.focuses.filter((item) =>
        isSupportedInterviewFocus(item.key),
      ),
    };
  },
};
