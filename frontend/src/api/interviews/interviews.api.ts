import { apiFetch } from "@/lib/fetch";
import type { Interview, InterviewFeedback, InterviewList, StartInterviewParams } from "./interviews.types";

export const interviewsApi = {
  start: async (
    params: StartInterviewParams,
    token: string,
  ): Promise<Interview> => {
    const res = await apiFetch("/interviews", {
      token,
      method: "POST",
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || "Request failed");
    }

    return res.json();
  },

  end: async (id: string, token: string): Promise<Interview> => {
    const res = await apiFetch(`/interviews/${id}/end`, {
      token,
      method: "POST",
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || "Request failed");
    }

    return res.json();
  },

  getById: async (id: string, token: string): Promise<Interview> => {
    const res = await apiFetch(`/interviews/${id}`, {
      token,
      method: "GET",
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || "Request failed");
    }

    return res.json();
  },

  getFeedback: async (id: string, token: string): Promise<InterviewFeedback | null> => {
    const res = await apiFetch(`/interviews/${id}/feedback`, {
      token,
      method: "GET",
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error("Could not load interview feedback");
    return res.json();
  },
  getReportPDF: async (id: string, token: string): Promise<Blob | null> => {
    const res = await apiFetch(`/interviews/${id}/report.pdf`, {
      token,
      method: "GET",
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error("Could not download PDF report");
    return res.blob();
  },

  list: async (token: string, page = 1): Promise<InterviewList> => {
    const res = await apiFetch(`/interviews?page=${page}&pageSize=10`, { token });
    if (!res.ok) throw new Error("Could not load interview history");
    return res.json();
  },
};
