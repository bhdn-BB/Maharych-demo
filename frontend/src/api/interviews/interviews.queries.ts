import { interviewsApi } from "./interviews.api";

export const interviewQueryKeys = {
  byId: (id: string) => ["interviews", id] as const,
} as const;

export const interviewQueries = {
  byId: (id: string, token: string) => ({
    queryKey: interviewQueryKeys.byId(id),
    queryFn: () => interviewsApi.getById(id, token),
    enabled: !!id && !!token,
  }),
} as const;
