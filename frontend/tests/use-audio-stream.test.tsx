// @vitest-environment jsdom
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useAudioStream } from "@/hooks/use-audio-stream";

vi.mock("@/hooks/use-backend-token", () => ({ useBackendToken: () => "token" }));
const requestAudioTicket = vi.hoisted(() => vi.fn(async () => "one-time-ticket"));
vi.mock("@/api/audio/audio", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/audio/audio")>()),
  requestAudioTicket,
}));

class Socket {
  static OPEN = 1;
  static instance: Socket;
  readyState = 1;
  binaryType = "";
  sent: unknown[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string | ArrayBuffer }) => void) | null = null;
  onerror: (() => void) | null = null;
  static urls: string[] = [];
  constructor(url: string) { Socket.urls.push(url); Socket.instance = this; queueMicrotask(() => this.onopen?.()); }
  send(data: unknown) { this.sent.push(data); }
  close() { this.readyState = 3; this.onclose?.(); }
  emit(value: object) { this.onmessage?.({ data: JSON.stringify(value) }); }
}

class Recorder {
  static isTypeSupported() { return true; }
  state = "inactive";
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  start() { this.state = "recording"; }
  stop() { this.state = "inactive"; this.ondataavailable?.({ data: new Blob(["answer"]) }); this.onstop?.(); }
}

beforeEach(() => {
  Socket.urls = [];
  requestAudioTicket.mockClear();
  vi.stubGlobal("WebSocket", Socket);
  vi.stubGlobal("MediaRecorder", Recorder);
  Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: {
    getUserMedia: vi.fn(async () => ({ getTracks: () => [{ stop: vi.fn() }] })),
  } });
  Object.defineProperty(Blob.prototype, "arrayBuffer", { configurable: true, value: async () => new ArrayBuffer(8) });
});
afterEach(() => { vi.unstubAllGlobals(); Reflect.deleteProperty(Blob.prototype, "arrayBuffer"); });

it("reserves the only attempt before accessing the microphone and sends it once", async () => {
  const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
  await waitFor(() => expect(result.current.connected).toBe(true));
  const socket = Socket.instance;
  act(() => socket.emit({ type: "STAGE_UPDATE", stage: "questioning", currentQuestion: 1, questionId: "q1" }));
  let started!: Promise<void>;
  act(() => { started = result.current.toggleRecording(); });
  const reservation = JSON.parse(socket.sent[0] as string);
  expect(reservation).toMatchObject({ type: "start_recording", questionId: "q1" });
  expect(navigator.mediaDevices.getUserMedia).not.toHaveBeenCalled();
  await act(async () => { socket.emit({ type: "STAGE_UPDATE", stage: "recording", questionId: "q1", answerId: reservation.answerId }); await started; });
  expect(result.current.recording).toBe(true);
  await act(async () => { await result.current.toggleRecording(); });
  await waitFor(() => expect(socket.sent).toHaveLength(3));
  expect(JSON.parse(socket.sent[1] as string)).toMatchObject({ type: "answer", answerId: reservation.answerId, questionId: "q1" });
  expect(result.current.canRecord).toBe(false);
  unmount();
});

it("skips the consumed attempt when microphone access is denied", async () => {
  vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValueOnce(new Error("denied"));
  const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
  await waitFor(() => expect(result.current.connected).toBe(true));
  const socket = Socket.instance;
  act(() => socket.emit({ type: "STAGE_UPDATE", stage: "questioning", currentQuestion: 1, questionId: "q1" }));
  let started!: Promise<void>;
  act(() => { started = result.current.toggleRecording(); });
  const reservation = JSON.parse(socket.sent[0] as string);
  await act(async () => { socket.emit({ type: "STAGE_UPDATE", stage: "recording", questionId: "q1", answerId: reservation.answerId }); await started; });
  expect(JSON.parse(socket.sent[1] as string)).toMatchObject({ type: "skip_recording", answerId: reservation.answerId });
  expect(result.current.canRecord).toBe(false);
  unmount();
});

it("does not consume the attempt when microphone access is already blocked", async () => {
  Object.defineProperty(navigator, "permissions", { configurable: true, value: { query: vi.fn(async () => ({ state: "denied" })) } });
  try {
    const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
    await waitFor(() => expect(result.current.connected).toBe(true));
    const socket = Socket.instance;
    act(() => socket.emit({ type: "STAGE_UPDATE", stage: "questioning", currentQuestion: 1, questionId: "q1" }));
    await act(async () => { await result.current.toggleRecording(); });
    expect(socket.sent).toHaveLength(0);
    expect(result.current.error).toMatch(/blocked/);
    expect(result.current.canRecord).toBe(true);
    unmount();
  } finally {
    Reflect.deleteProperty(navigator, "permissions");
  }
});

it("does not consume the attempt when the browser cannot record", async () => {
  vi.stubGlobal("MediaRecorder", class { static isTypeSupported() { return false; } });
  const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
  await waitFor(() => expect(result.current.connected).toBe(true));
  const socket = Socket.instance;
  act(() => socket.emit({ type: "STAGE_UPDATE", stage: "questioning", currentQuestion: 1, questionId: "q1" }));
  await act(async () => { await result.current.toggleRecording(); });
  expect(socket.sent).toHaveLength(0);
  expect(result.current.error).toMatch(/cannot record/);
  unmount();
});

it("stops the recording after 120 seconds", async () => {
  const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
  await waitFor(() => expect(result.current.connected).toBe(true));
  const socket = Socket.instance;
  act(() => socket.emit({ type: "STAGE_UPDATE", stage: "questioning", currentQuestion: 1, questionId: "q1" }));
  vi.useFakeTimers();
  try {
    let started!: Promise<void>;
    act(() => { started = result.current.toggleRecording(); });
    const reservation = JSON.parse(socket.sent[0] as string);
    await act(async () => { socket.emit({ type: "STAGE_UPDATE", stage: "recording", questionId: "q1", answerId: reservation.answerId }); await started; });
    act(() => vi.advanceTimersByTime(119000));
    expect(result.current.recording).toBe(true);
    act(() => vi.advanceTimersByTime(1000));
    expect(result.current.recording).toBe(false);
    expect(result.current.recordingSeconds).toBe(120);
  } finally {
    unmount();
    vi.useRealTimers();
  }
});

it("shows the question while it is read aloud and unlocks recording when audio ends", async () => {
  const player = { play: vi.fn().mockResolvedValue(undefined), pause: vi.fn(), onended: null as (() => void) | null, onplaying: null as (() => void) | null, onerror: null, currentTime: 0 };
  vi.stubGlobal("Audio", vi.fn(function () { return player; }));
  vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:audio"), revokeObjectURL: vi.fn() });
  const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
  await waitFor(() => expect(result.current.connected).toBe(true));
  const socket = Socket.instance;
  act(() => {
    socket.emit({ type: "AI_TEXT", stage: "questioning", currentQuestion: 1, questionId: "q1", text: "Question?" });
    socket.emit({ type: "STAGE_UPDATE", stage: "questioning", currentQuestion: 1, questionId: "q1" });
    socket.emit({ type: "AI_AUDIO", questionId: "q1", audioMimeType: "audio/mpeg" });
    socket.onmessage?.({ data: new ArrayBuffer(8) });
  });
  // Text waits for the voice so both appear together.
  expect(result.current.messages.some((message) => message.text === "Question?")).toBe(false);
  expect(result.current.canRecord).toBe(false);
  act(() => player.onplaying?.());
  expect(result.current.messages.filter((message) => message.text === "Question?")).toHaveLength(1);
  expect(result.current.questionPlaying).toBe(true);
  expect(result.current.canRecord).toBe(false);
  act(() => player.onended?.());
  expect(result.current.messages.filter((message) => message.text === "Question?")).toHaveLength(1);
  expect(result.current.questionPlaying).toBe(false);
  expect(result.current.canRecord).toBe(true);
  unmount();
});

it("Stop audio ends playback early and unlocks recording", async () => {
  const player = { play: vi.fn().mockResolvedValue(undefined), pause: vi.fn(), onended: null as (() => void) | null, onplaying: null as (() => void) | null, onerror: null, currentTime: 0 };
  vi.stubGlobal("Audio", vi.fn(function () { return player; }));
  vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:audio"), revokeObjectURL: vi.fn() });
  const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
  await waitFor(() => expect(result.current.connected).toBe(true));
  const socket = Socket.instance;
  act(() => {
    socket.emit({ type: "AI_TEXT", stage: "questioning", currentQuestion: 1, questionId: "q1", text: "Question?" });
    socket.emit({ type: "STAGE_UPDATE", stage: "questioning", currentQuestion: 1, questionId: "q1" });
    socket.emit({ type: "AI_AUDIO", questionId: "q1", audioMimeType: "audio/mpeg" });
    socket.onmessage?.({ data: new ArrayBuffer(8) });
  });
  act(() => player.onplaying?.());
  expect(result.current.canRecord).toBe(false);
  act(() => result.current.stopAudio());
  expect(player.pause).toHaveBeenCalled();
  expect(result.current.questionPlaying).toBe(false);
  expect(result.current.canRecord).toBe(true);
  unmount();
});

it("keeps the question answerable when the AI provider is temporarily unavailable", async () => {
  const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
  await waitFor(() => expect(result.current.connected).toBe(true));
  const socket = Socket.instance;
  act(() => {
    socket.emit({ type: "AI_TEXT", stage: "questioning", currentQuestion: 1, questionId: "q1", text: "Question?" });
    socket.emit({ type: "ERROR", answerId: "a1", error: "The AI service is temporarily unavailable" });
    socket.emit({ type: "STAGE_UPDATE", stage: "questioning", currentQuestion: 1, questionId: "q1" });
  });
  expect(result.current.error).toContain("temporarily unavailable");
  expect(result.current.canRecord).toBe(true);
  unmount();
});

it("reveals the question when speech synthesis fails", async () => {
  const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
  await waitFor(() => expect(result.current.connected).toBe(true));
  const socket = Socket.instance;
  act(() => {
    socket.emit({ type: "AI_TEXT", stage: "questioning", currentQuestion: 1, questionId: "q1", text: "Question?" });
    socket.emit({ type: "ERROR", error: "Speech unavailable" });
  });
  expect(result.current.messages.some((message) => message.text === "Question?")).toBe(true);
  unmount();
});

it("opens the socket with a one-time ticket and never puts the API token in the URL", async () => {
  const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
  await waitFor(() => expect(result.current.connected).toBe(true));
  expect(requestAudioTicket).toHaveBeenCalledWith("id", "token");
  expect(Socket.urls[0]).toContain("ticket=one-time-ticket");
  expect(Socket.urls[0]).not.toContain("token=");
  unmount();
});

it("reports a ticket failure without opening a socket", async () => {
  requestAudioTicket.mockRejectedValueOnce(new Error("interview not found"));
  const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
  await waitFor(() => expect(result.current.error).toBe("interview not found"));
  expect(Socket.urls).toHaveLength(0);
  unmount();
});

it("shows the question text after 5 s when its audio has not started", async () => {
  const { result, unmount } = renderHook(() => useAudioStream({ interviewId: "id", enabled: true }));
  await waitFor(() => expect(result.current.connected).toBe(true));
  vi.useFakeTimers();
  try {
    act(() => {
      Socket.instance.emit({ type: "AI_TEXT", stage: "questioning", currentQuestion: 1, questionId: "q1", text: "Question?" });
    });
    act(() => vi.advanceTimersByTime(4900));
    expect(result.current.messages.some((m) => m.text === "Question?")).toBe(false);
    act(() => vi.advanceTimersByTime(200));
    expect(result.current.messages.filter((m) => m.text === "Question?")).toHaveLength(1);
    expect(result.current.canRecord).toBe(false); // still waiting for the voice or an error
  } finally {
    vi.useRealTimers();
    unmount();
  }
});
