import { useCallback, useRef } from "react";

export function useQuestionAudio(setError: (message: string) => void) {
  const player = useRef<HTMLAudioElement | null>(null);
  const url = useRef<string | null>(null);
  const question = useRef("");

  const completion = useRef<(() => void) | null>(null);
  const finish = useCallback(() => {
    const callback = completion.current;
    completion.current = null;
    callback?.();
  }, []);
  const stop = useCallback(() => { player.current?.pause(); finish(); }, [finish]);
  const cleanup = useCallback(() => {
    stop();
    if (url.current) URL.revokeObjectURL(url.current);
    url.current = null;
  }, [stop]);
  const play = useCallback(
    (
      bytes: ArrayBuffer,
      mimeType: string,
      questionId: string,
      onComplete?: () => void,
      onStart?: () => void,
    ) => {
      stop();
      if (url.current) URL.revokeObjectURL(url.current);
      url.current = URL.createObjectURL(new Blob([bytes], { type: mimeType }));
      player.current = new Audio(url.current);
      completion.current = onComplete ?? null;
      player.current.onplaying = () => onStart?.();
      player.current.onended = finish;
      player.current.onerror = finish;
      question.current = questionId;
      void player.current
        .play()
        .catch(() => { setError("Press Replay audio to hear the question."); finish(); });
    },
    [finish, setError, stop],
  );
  const replay = useCallback(
    (questionId: string): boolean => {
      if (!player.current || question.current !== questionId) return false;
      player.current.currentTime = 0;
      void player.current
        .play()
        .catch(() => setError("Could not play question audio"));
      return true;
    },
    [setError],
  );
  return { stop, cleanup, play, replay };
}
