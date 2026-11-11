import { useMutation, useQuery } from "@tanstack/react-query";
import { interviewsApi } from "@/api/interviews/interviews.api";
import { interviewQueries } from "@/api/interviews/interviews.queries";
import { useBackendToken } from "@/hooks/use-backend-token";
import type { StartInterviewParams } from "@/api/interviews/interviews.types";

export function useStartInterview() {
  const token = useBackendToken();

  return useMutation({
    mutationFn: (params: StartInterviewParams) =>
      interviewsApi.start(params, token),
  });
}

export function useEndInterview() {
  const token = useBackendToken();

  return useMutation({
    mutationFn: (id: string) => interviewsApi.end(id, token),
  });
}

export function useInterview(id: string | null) {
  const token = useBackendToken();

  return useQuery({
    ...interviewQueries.byId(id!, token),
    enabled: !!id && !!token,
    // Finalization is asynchronous: keep polling until the backend stores a terminal status.
    refetchInterval: (query) =>
      query.state.data?.status === "finalizing" ? 2000 : false,
  });
}

export function useInterviewFeedback(id: string | null, ready = true) {
  const token = useBackendToken();
  return useQuery({
    queryKey: ["interviews", id, "feedback"],
    queryFn: () => interviewsApi.getFeedback(id!, token),
    enabled: !!id && !!token && ready,
    retry: false,
  });
}

export function useInterviewHistory(page = 1) {
  const token = useBackendToken();
  return useQuery({
    queryKey: ["interviews", "history", page],
    queryFn: () => interviewsApi.list(token, page),
    enabled: !!token,
  });
}
