// @vitest-environment jsdom

import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useQuestionAudio } from "@/hooks/use-question-audio";

afterEach(() => vi.unstubAllGlobals());

it("replays only the current question and releases playback resources", () => {
  const pause = vi.fn();
  const play = vi.fn().mockResolvedValue(undefined);
  const audio = { pause, play, currentTime: 5 };
  const create = vi.fn().mockReturnValue("blob:question");
  const revoke = vi.fn();
  vi.stubGlobal(
    "Audio",
    vi.fn(function () {
      return audio;
    }),
  );
  vi.stubGlobal("URL", { createObjectURL: create, revokeObjectURL: revoke });
  const { result } = renderHook(() => useQuestionAudio(vi.fn()));

  act(() => result.current.play(new ArrayBuffer(1), "audio/mpeg", "q1"));
  expect(result.current.replay("q2")).toBe(false);
  expect(result.current.replay("q1")).toBe(true);
  expect(audio.currentTime).toBe(0);
  expect(play).toHaveBeenCalledTimes(2);
  act(() => result.current.cleanup());
  expect(pause).toHaveBeenCalled();
  expect(revoke).toHaveBeenCalledWith("blob:question");
});
