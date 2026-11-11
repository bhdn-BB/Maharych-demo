// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const stream = vi.hoisted(() => ({
  connected: true,
  currentQuestion: 0,
  waitingForQuestion: true,
  processing: false,
  messages: [] as { id: number; type: string }[],
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
vi.mock("@/hooks/use-interview", () => ({
  useInterview: () => ({ data: { id: "id", status: "in_progress", startedAt: new Date(0).toISOString() }, isLoading: false }),
  useEndInterview: () => ({ mutate: vi.fn(), isPending: false }),
}));
vi.mock("@/hooks/use-audio-stream", () => ({
  useAudioStream: () => ({
    ...stream,
    reconnect: vi.fn(), replayAudio: vi.fn(), stopAudio: vi.fn(), recordingSeconds: 0,
    totalQuestions: 5, error: null, recording: false, canRecord: true, stage: "questioning",
    toggleRecording: vi.fn(), cleanup: vi.fn(),
  }),
}));

import { useInterviewSession } from "@/components/pages/interview/hooks/useInterviewSession";

beforeEach(() => { vi.useFakeTimers(); window.sessionStorage.clear(); });
afterEach(() => vi.useRealTimers());

it("keeps the clock paused until the question is on screen", () => {
  Object.assign(stream, { currentQuestion: 0, waitingForQuestion: true, messages: [] });
  const { result, rerender } = renderHook(() => useInterviewSession("id"));
  act(() => vi.advanceTimersByTime(10000));
  expect(result.current.time).toBe(0);
  expect(result.current.clockPaused).toBe(true);

  Object.assign(stream, { currentQuestion: 1, waitingForQuestion: false, messages: [{ id: 1, type: "AI_TEXT" }] });
  rerender();
  act(() => vi.advanceTimersByTime(3000));
  expect(result.current.time).toBe(3);
  expect(result.current.clockPaused).toBe(false);

  Object.assign(stream, { processing: true });
  rerender();
  act(() => vi.advanceTimersByTime(5000));
  expect(result.current.time).toBe(3);
});
