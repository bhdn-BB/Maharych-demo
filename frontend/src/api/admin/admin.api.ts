import { apiFetch } from "@/lib/fetch";

export type AdminOption = {
  ID: number;
  category: "level" | "position" | "focus";
  key: string;
  label: string;
  description?: string | null;
  icon: string;
  sortOrder: number;
};

export type AdminOptionInput = Omit<AdminOption, "ID">;

export type AdminQuestion = {
  id: number;
  key: string;
  version: number;
  language: string;
  focus: string;
  topicIndex: number;
  role: string;
  level: string;
  question: string;
  criteria: string;
  active: boolean;
};

export type AdminOutboxEntry = {
  interviewId: string;
  published: boolean;
  attempts: number;
  createdAt: string;
  publishedAt: string | null;
  lastError: string | null;
};

async function request<T>(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await apiFetch(`/admin${path}`, { token, ...init });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
});

export const adminApi = {
  options: (t: string) => request<AdminOption[]>("/interview-options", t),
  createOption: (t: string, b: AdminOptionInput) =>
    request<AdminOption>("/interview-options", t, json("POST", b)),
  updateOption: (t: string, id: number, b: AdminOptionInput) =>
    request<AdminOption>(`/interview-options/${id}`, t, json("PUT", b)),
  deleteOption: (t: string, id: number) =>
    request<void>(`/interview-options/${id}`, t, { method: "DELETE" }),

  questions: (t: string, q: { language?: string; focus?: string }) => {
    const p = new URLSearchParams();
    if (q.language) p.set("language", q.language);
    if (q.focus) p.set("focus", q.focus);
    return request<AdminQuestion[]>(`/questions?${p}`, t);
  },
  updateQuestion: (
    t: string,
    id: number,
    b: Partial<Pick<AdminQuestion, "question" | "criteria" | "active">>,
  ) => request<AdminQuestion>(`/questions/${id}`, t, json("PUT", b)),
  newQuestionVersion: (
    t: string,
    b: { sourceId: number; question: string; criteria: string },
  ) => request<AdminQuestion>("/questions", t, json("POST", b)),

  outbox: (t: string, pending: boolean) =>
    request<AdminOutboxEntry[]>(`/feedback-outbox?pending=${pending}`, t),
  retryOutbox: (t: string, interviewId: string) =>
    request<void>(`/feedback-outbox/${interviewId}/retry`, t, {
      method: "POST",
    }),
};
