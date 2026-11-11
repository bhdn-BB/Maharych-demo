"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/fetch";
import { useBackendToken } from "@/hooks/use-backend-token";

export const voices = [
  { id: "anna", name: "Anna", description: "Clear and assured" },
  { id: "sophia", name: "Sophia", description: "Light and relaxed" },
  { id: "daniel", name: "Daniel", description: "Calm and informative" },
  { id: "alex", name: "Alex", description: "Friendly and upbeat" },
] as const;
export type VoiceId = (typeof voices)[number]["id"];

export function VoiceSelector({ value, onChange, language }: {
  value: VoiceId; onChange: (value: VoiceId) => void; language: "" | "uk" | "en";
}) {
  const token = useBackendToken();
  const [playing, setPlaying] = useState<VoiceId | null>(null);
  const [error, setError] = useState("");
  const audio = useRef<HTMLAudioElement | null>(null);
  const objectUrl = useRef<string | null>(null);
  const request = useRef<AbortController | null>(null);

  const stop = () => {
    request.current?.abort();
    request.current = null;
    audio.current?.pause();
    audio.current = null;
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    objectUrl.current = null;
  };
  useEffect(() => () => stop(), []);

  const preview = async (id: VoiceId) => {
    stop();
    if (playing === id) { setPlaying(null); return; }
    if (!language || !token) { setError("Choose a language and sign in to preview voices."); setPlaying(null); return; }
    setError("");
    setPlaying(id);
    const controller = new AbortController();
    request.current = controller;
    try {
      const response = await apiFetch(`/voices/${id}/preview?language=${language}`, { token, signal: controller.signal });
      if (!response.ok) throw new Error("Voice preview is unavailable. Please try again.");
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      objectUrl.current = URL.createObjectURL(blob);
      const player = new Audio(objectUrl.current);
      audio.current = player;
      player.onended = () => { stop(); setPlaying(null); };
      await player.play();
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : "Voice preview is unavailable.");
        stop(); setPlaying(null);
      }
    }
  };

  return <fieldset className="space-y-3">
    <legend className="text-xl font-semibold">Interviewer voice</legend>
    <p className="text-sm text-muted-foreground">Choose a voice and preview it in your interview language.</p>
    <div className="grid gap-3 sm:grid-cols-2">
      {voices.map((voice) => <div key={voice.id} className="flex items-center justify-between gap-3 rounded-xl border border-border p-4">
        <label className="flex cursor-pointer items-center gap-3">
          <input type="radio" name="interviewer-voice" checked={value === voice.id} onChange={() => onChange(voice.id)} />
          <span><span className="block font-medium">{voice.name}</span><span className="text-sm text-muted-foreground">{voice.description}</span></span>
        </label>
        <button type="button" onClick={() => void preview(voice.id)} className="rounded-md px-3 py-2 text-sm text-primary hover:bg-primary/10 focus-visible:outline focus-visible:outline-2" aria-label={`${playing === voice.id ? "Stop" : "Preview"} ${voice.name}`}>
          {playing === voice.id ? "Stop" : "Preview"}
        </button>
      </div>)}
    </div>
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
  </fieldset>;
}
