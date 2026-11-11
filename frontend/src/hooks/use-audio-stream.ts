import { useCallback, useEffect, useRef, useState } from "react";
import { getAudioStreamUrl, requestAudioTicket } from "@/api/audio/audio";
import { useBackendToken } from "@/hooks/use-backend-token";
import { useQuestionAudio } from "@/hooks/use-question-audio";

export interface AudioStreamMessage {
  id: number;
  type: string;
  transcription?: string;
  text?: string;
  stage?: string;
  currentQuestion?: number;
  totalQuestions?: number;
  error?: string;
  questionId?: string;
  answerId?: string;
  eventId?: string;
  audioMimeType?: string;
}

export const QUESTION_TEXT_FALLBACK_MS = 5000;

export function useAudioStream({
  interviewId,
  enabled,
}: {
  interviewId: string;
  enabled: boolean;
}) {
  const token = useBackendToken();
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<AudioStreamMessage[]>([]);
  const [stage, setStage] = useState("");
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [waitingForQuestion, setWaitingForQuestion] = useState(false);
  // The question text is shown as soon as it arrives; recording stays locked
  // while its audio plays (questionPlaying) so the answer never overlaps the voice.
  const [questionPlaying, setQuestionPlaying] = useState(false);
  const [connectionAttempt, setConnectionAttempt] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const startingRef = useRef(false);
  const sendOnStopRef = useRef(false);
  const activeRef = useRef(false);
  const msgIdRef = useRef(0);
  const questionRef = useRef("");
  const audioMetadataRef = useRef<AudioStreamMessage | null>(null);
  const queuedQuestionRef = useRef<AudioStreamMessage | null>(null);
  // Text and voice appear together: the question is shown when its audio starts
  // playing, or after QUESTION_TEXT_FALLBACK_MS if no audio has started by then.
  const fallbackRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showQuestion = useCallback((msg: AudioStreamMessage) => {
    setMessages((prev) =>
      prev.some(
        (m) =>
          m.type === "AI_TEXT" &&
          m.questionId === msg.questionId &&
          m.text === msg.text,
      )
        ? prev
        : [...prev, { ...msg, id: ++msgIdRef.current }],
    );
  }, []);
  const clearFallback = useCallback(() => {
    if (fallbackRef.current) clearTimeout(fallbackRef.current);
    fallbackRef.current = null;
  }, []);
  const revealQuestion = useCallback(() => {
    if (fallbackRef.current) clearTimeout(fallbackRef.current);
    fallbackRef.current = null;
    const msg = queuedQuestionRef.current;
    queuedQuestionRef.current = null;
    setWaitingForQuestion(false);
    setQuestionPlaying(false);
    if (msg)
      setMessages((prev) =>
        prev.some(
          (m) =>
            m.type === "AI_TEXT" &&
            m.questionId === msg.questionId &&
            m.text === msg.text,
        )
          ? prev
          : [...prev, { ...msg, id: ++msgIdRef.current }],
      );
  }, []);
  const {
    stop: stopAudio,
    cleanup: cleanupAudio,
    play: playAudio,
    replay: replayQuestionAudio,
  } = useQuestionAudio(setError);
  const pendingRef = useRef<{
    answerId: string;
    questionId: string;
    bytes: ArrayBuffer;
  } | null>(null);
  const reservationRef = useRef<{
    id: string;
    question: string;
    resolve: (ok: boolean) => void;
  } | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const seenRef = useRef(new Set<string>());

  const clearWait = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = null;
    setProcessing(false);
  }, []);
  const stopRecordingTimer = useCallback(() => {
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    recordingTimerRef.current = null;
  }, []);
  const cleanup = useCallback(() => {
    reservationRef.current?.resolve(false);
    reservationRef.current = null;
    pendingRef.current = null;
    activeRef.current = false;
    sendOnStopRef.current = false;
    stopRecordingTimer();
    if (recorderRef.current?.state !== "inactive") recorderRef.current?.stop();
    recorderRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    const ws = wsRef.current;
    wsRef.current = null;
    if (ws) {
      ws.onclose = null;
      ws.onmessage = null;
      ws.close();
    }
    cleanupAudio();
    clearWait();
    setConnected(false);
    setRecording(false);
  }, [clearWait, cleanupAudio, stopRecordingTimer]);

  const sendPending = useCallback(() => {
    const ws = wsRef.current,
      pending = pendingRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !pending) return;
    clearWait();
    setProcessing(true);
    setError(null);
    ws.send(
      JSON.stringify({
        type: "answer",
        answerId: pending.answerId,
        questionId: pending.questionId,
      }),
    );
    ws.send(pending.bytes);
    timeoutRef.current = setTimeout(() => {
      setProcessing(false);
      setError("Processing is taking too long. Reconnect to continue.");
    }, 65000);
  }, [clearWait]);

  useEffect(() => {
    if (!enabled || !token || !interviewId) return;
    activeRef.current = true;
    setCurrentQuestion(0);
    let cancelled = false;
    const open = (ticket: string) => {
      const ws = new WebSocket(getAudioStreamUrl(interviewId, ticket));
      wsRef.current = ws;
      ws.binaryType = "arraybuffer";
      ws.onopen = () => {
        setConnected(true);
        setError(null);
      };
      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          const meta = audioMetadataRef.current;
          if (meta?.questionId && meta.questionId !== questionRef.current)
            return;
          if (recorderRef.current || startingRef.current) return;
          playAudio(
            event.data,
            meta?.audioMimeType || "audio/mpeg",
            meta?.questionId || "",
            revealQuestion,
            () => {
              clearFallback();
              if (queuedQuestionRef.current) showQuestion(queuedQuestionRef.current);
              setQuestionPlaying(true);
            },
          );
          return;
        }
        try {
          const msg: AudioStreamMessage = JSON.parse(event.data);
          if (msg.type === "AI_AUDIO") {
            audioMetadataRef.current = msg;
            return;
          }
          if (msg.eventId && seenRef.current.has(msg.eventId)) return;
          if (msg.eventId) seenRef.current.add(msg.eventId);
          if (msg.questionId && msg.type !== "TRANSCRIPTION") {
            if (questionRef.current !== msg.questionId) {
              stopAudio();
              pendingRef.current = null;
            }
            questionRef.current = msg.questionId;
          }
          if (msg.stage) setStage(msg.stage);
          if (msg.currentQuestion !== undefined)
            setCurrentQuestion(msg.currentQuestion);
          if (msg.totalQuestions !== undefined)
            setTotalQuestions(msg.totalQuestions);
          if (msg.type === "ERROR") {
            revealQuestion();
            reservationRef.current?.resolve(false);
            reservationRef.current = null;
            pendingRef.current = null;
            setError(msg.error || "Processing failed");
            if (msg.answerId || !pendingRef.current) clearWait();
            return;
          }
          if (
            msg.type === "TRANSCRIPTION" &&
            pendingRef.current?.answerId === msg.answerId
          ) {
            pendingRef.current = null;
          }
          if (
            msg.type === "STAGE_UPDATE" &&
            msg.stage === "recording" &&
            reservationRef.current?.id === msg.answerId
          ) {
            reservationRef.current.resolve(true);
            reservationRef.current = null;
          }
          if (
            ["AI_TEXT", "STAGE_UPDATE", "INTERVIEW_FINISHED"].includes(msg.type)
          )
            clearWait();
          if (msg.type === "AI_TEXT" && msg.stage === "questioning") {
            queuedQuestionRef.current = msg;
            setWaitingForQuestion(true);
            clearFallback();
            fallbackRef.current = setTimeout(() => {
              fallbackRef.current = null;
              if (queuedQuestionRef.current) showQuestion(queuedQuestionRef.current);
            }, QUESTION_TEXT_FALLBACK_MS);
            return;
          }
          if (["TRANSCRIPTION", "AI_TEXT"].includes(msg.type)) {
            setMessages((prev) => {
              if (
                msg.type === "AI_TEXT" &&
                msg.questionId &&
                prev.some(
                  (m) =>
                    m.type === "AI_TEXT" &&
                    m.questionId === msg.questionId &&
                    m.text === msg.text,
                )
              )
                return prev;
              return [...prev, { ...msg, id: ++msgIdRef.current }];
            });
          }
        } catch {
          setError(
            "Could not read an interview event. Reconnect to restore the session.",
          );
        }
      };
      ws.onclose = () => {
        revealQuestion();
        reservationRef.current?.resolve(false);
        reservationRef.current = null;
        pendingRef.current = null;
        setConnected(false);
        setRecording(false);
        clearWait();
        stopRecordingTimer();
        sendOnStopRef.current = false;
        if (recorderRef.current?.state !== "inactive")
          recorderRef.current?.stop();
        recorderRef.current = null;
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        stopAudio();
      };
      ws.onerror = () =>
        setError("Connection failed. Reconnect to restore the session.");
    };
    requestAudioTicket(interviewId, token)
      .then((ticket) => {
        if (!cancelled) open(ticket);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(
            err instanceof Error
              ? err.message
              : "Connection failed. Reconnect to restore the session.",
          );
      });
    return () => {
      cancelled = true;
      cleanup();
    };
  }, [
    enabled,
    token,
    interviewId,
    connectionAttempt,
    cleanup,
    clearWait,
    stopAudio,
    playAudio,
    stopRecordingTimer,
    revealQuestion,
    showQuestion,
    clearFallback,
  ]);

  const toggleRecording = useCallback(async () => {
    const recorder = recorderRef.current;
    if (recorder?.state === "recording") {
      recorder.stop();
      setRecording(false);
      return;
    }
    if (
      recorder ||
      startingRef.current ||
      processing ||
      waitingForQuestion ||
      pendingRef.current ||
      currentQuestion === 0 ||
      ["finished", "abandoned", "recording"].includes(stage)
    )
      return;
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setError("Interview connection is not ready");
      return;
    }
    // Checks that do not touch the microphone run before the attempt is reserved,
    // so an unsupported browser or an already blocked permission never consumes a question.
    if (
      typeof MediaRecorder === "undefined" ||
      !MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ) {
      setError(
        "This browser cannot record answers. Use a recent Chrome, Edge or Firefox.",
      );
      return;
    }
    startingRef.current = true;
    const permission = navigator.permissions
      ? await navigator.permissions
          .query({ name: "microphone" as PermissionName })
          .catch(() => null)
      : null;
    if (permission?.state === "denied") {
      startingRef.current = false;
      setError(
        "Microphone access is blocked. Allow it in the browser address bar, then press record again — the question was not used.",
      );
      return;
    }
    if (wsRef.current !== ws || ws.readyState !== WebSocket.OPEN) {
      startingRef.current = false;
      setError("Interview connection is not ready");
      return;
    }
    stopAudio();
    const questionId = questionRef.current;
    const answerId = crypto.randomUUID();
    const skip = () => {
      if (ws.readyState === WebSocket.OPEN)
        ws.send(
          JSON.stringify({ type: "skip_recording", questionId, answerId }),
        );
      else setError("Connection closed. Reconnect to continue.");
    };
    try {
      setProcessing(true);
      const reserved = await new Promise<boolean>((resolve) => {
        const timer = setTimeout(() => {
          reservationRef.current = null;
          setError("Connection timed out. Reconnect to continue.");
          ws.close();
          resolve(false);
        }, 15000);
        reservationRef.current = {
          id: answerId,
          question: questionId,
          resolve: (ok) => {
            clearTimeout(timer);
            resolve(ok);
          },
        };
        ws.send(
          JSON.stringify({ type: "start_recording", questionId, answerId }),
        );
      });
      if (!reserved) {
        clearWait();
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          channelCount: 1,
        },
      });
      if (
        !activeRef.current ||
        wsRef.current !== ws ||
        ws.readyState !== WebSocket.OPEN
      ) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      streamRef.current = stream;
      const chunks: Blob[] = [];
      const nextRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });
      recorderRef.current = nextRecorder;
      nextRecorder.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      nextRecorder.onstop = async () => {
        stopRecordingTimer();
        setRecording(false);
        if (recorderRef.current === nextRecorder) recorderRef.current = null;
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        if (!sendOnStopRef.current) return;
        sendOnStopRef.current = false;
        const answer = new Blob(chunks, { type: "audio/webm;codecs=opus" });
        if (!answer.size || answer.size > 8 * 1024 * 1024) {
          skip();
          return;
        }
        startingRef.current = true;
        setProcessing(true);
        try {
          const bytes = await answer.arrayBuffer();
          if (!activeRef.current) return;
          pendingRef.current = {
            answerId,
            questionId,
            bytes,
          };
          if (ws.readyState === WebSocket.OPEN) sendPending();
          else {
            clearWait();
            setError("Connection closed. Reconnect to continue.");
          }
        } catch {
          clearWait();
          skip();
        } finally {
          startingRef.current = false;
        }
      };
      nextRecorder.onerror = () => {
        sendOnStopRef.current = false;
        stopRecordingTimer();
        stream.getTracks().forEach((t) => t.stop());
        if (nextRecorder.state === "recording") nextRecorder.stop();
        setRecording(false);
        skip();
      };
      sendOnStopRef.current = true;
      nextRecorder.start();
      setProcessing(false);
      setRecording(true);
      setRecordingSeconds(0);
      setError(null);
      let seconds = 0;
      recordingTimerRef.current = setInterval(() => {
        seconds += 1;
        setRecordingSeconds(seconds);
        if (seconds >= 120 && nextRecorder.state === "recording")
          nextRecorder.stop();
      }, 1000);
    } catch {
      sendOnStopRef.current = false;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      recorderRef.current = null;
      streamRef.current = null;
      setRecording(false);
      setError(
        "Microphone access was denied or is unavailable, so this question was skipped.",
      );
      skip();
    } finally {
      startingRef.current = false;
    }
  }, [
    processing,
    waitingForQuestion,
    currentQuestion,
    stage,
    sendPending,
    stopAudio,
    stopRecordingTimer,
    clearWait,
  ]);

  const replayAudio = useCallback(() => {
    if (!replayQuestionAudio(questionRef.current))
      wsRef.current?.send(
        JSON.stringify({
          type: "replay_audio",
          questionId: questionRef.current,
        }),
      );
  }, [replayQuestionAudio]);
  return {
    connected,
    messages,
    stage,
    currentQuestion,
    totalQuestions,
    error,
    recording,
    processing,
    recordingSeconds,
    waitingForQuestion,
    questionPlaying,
    replayAudio,
    stopAudio,
    reconnect: () => setConnectionAttempt((n) => n + 1),
    canRecord:
      connected &&
      currentQuestion > 0 &&
      !["finished", "abandoned", "recording"].includes(stage) &&
      !processing &&
      !waitingForQuestion &&
      !pendingRef.current,
    toggleRecording,
    cleanup,
  };
}
