import { interviewOptionsApi } from "./interview-options.api";

export const interviewOptionQueryKeys = {
  all: () => ["interview-options"] as const,
} as const;

export const interviewOptionQueries = {
  all: () => ({
    queryKey: interviewOptionQueryKeys.all(),
    queryFn: () => interviewOptionsApi.getAll(),
    staleTime: 3600 * 1000,
  }),
} as const;
