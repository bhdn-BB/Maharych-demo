import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useInterview, useEndInterview } from "@/hooks/use-interview";
import { useAudioStream } from "@/hooks/use-audio-stream";

export function useInterviewSession(interviewId: string) {
  const router = useRouter();
  const { data: interview, isLoading } = useInterview(interviewId ?? null);
  const endInterview = useEndInterview();

  const [time, setTime] = useState(0);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const finishRequestedRef = useRef(false);

  const isInProgress = interview?.status === "in_progress";

  const {
    connected,
    reconnect,
    replayAudio,
    stopAudio,
    recordingSeconds,
    messages,
    currentQuestion,
    totalQuestions,
    error: streamError,
    recording,
    canRecord,
    processing,
    waitingForQuestion,
    questionPlaying,
    stage,
    toggleRecording,
    cleanup: cleanupStream,
  } = useAudioStream({
    interviewId,
    enabled: !!interview && isInProgress,
  });

  // The clock only runs while a question is on screen and can be answered, so the
  // time spent generating and voicing questions or evaluating answers is not counted.
  const questionVisible = messages.some((m) => m.type === "AI_TEXT");
  const answering =
    isInProgress &&
    connected &&
    currentQuestion > 0 &&
    questionVisible &&
    !waitingForQuestion &&
    !processing;
  const timeKey = `interview-time:${interviewId}`;

  useEffect(() => {
    try {
      const saved = Number(window.sessionStorage.getItem(timeKey));
      if (Number.isFinite(saved) && saved > 0) setTime(saved);
    } catch {
      /* storage unavailable: start from zero */
    }
  }, [timeKey]);

  useEffect(() => {
    if (!answering) return;
    const timer = setInterval(() => {
      setTime((t) => {
        const next = t + 1;
        try {
          window.sessionStorage.setItem(timeKey, String(next));
        } catch {
          /* ignore */
        }
        return next;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [answering, timeKey]);

  useEffect(() => {
    if (!isInProgress) return;
    const warn = (event: BeforeUnloadEvent) => {
      if (finishRequestedRef.current) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isInProgress]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (streamError) {
      toast.error(streamError);
    }
  }, [streamError]);

  const handleMicToggle = () => {
    void toggleRecording();
  };

  const handleEnd = useCallback(() => {
    if (finishRequestedRef.current) return;
    finishRequestedRef.current = true;
    endInterview.mutate(interviewId, {
      onSuccess: () => {
        cleanupStream();
        toast.success("Interview ended");
        router.push(`/interview/${interviewId}/result`);
      },
      onError: (err) => {
        finishRequestedRef.current = false;
        toast.error(err.message || "Failed to end interview");
      },
    });
  }, [cleanupStream, endInterview, interviewId, router]);

  useEffect(() => {
    if (
      (stage === "finished" || stage === "abandoned") &&
      !finishRequestedRef.current
    ) {
      handleEnd();
    }
  }, [stage, handleEnd]);

  return {
    interview,
    reconnect,
    replayAudio,
    stopAudio,
    recordingSeconds,
    streamError,
    isLoading,
    isInProgress,
    time,
    micOn: recording,
    canRecord,
    processing,
    waitingForQuestion,
    questionPlaying,
    handleMicToggle,
    connected,
    messages,
    currentQuestion,
    totalQuestions,
    chatEndRef,
    handleEnd,
    isEnding: endInterview.isPending,
    clockPaused: isInProgress && !answering,
  };
}
