import { RefObject } from "react";
import { AnimatePresence } from "framer-motion";
import { ChatMessage } from "./ChatMessage";
import { ChatEmpty } from "./ChatEmpty";
import type { AudioStreamMessage } from "@/hooks/use-audio-stream";

interface ChatPanelProps {
  connected: boolean;
  processing: boolean;
  waitingForQuestion: boolean;
  questionPlaying?: boolean;
  messages: AudioStreamMessage[];
  chatEndRef: RefObject<HTMLDivElement | null>;
}

export function ChatPanel({ connected, processing, waitingForQuestion, questionPlaying, messages, chatEndRef }: ChatPanelProps) {
  return (
    <div className="flex-[1] glass rounded-2xl flex flex-col min-w-0 glow-border overflow-hidden">
      <div className="px-5 py-4 border-b border-border/20">
        <h3 className="font-display font-semibold text-sm">AI Interviewer</h3>
        <p className="text-xs text-muted-foreground mt-0.5">
          {questionPlaying ? "Reading the question aloud…" : waitingForQuestion ? "Preparing the question…" : processing ? "Evaluating your answer…" : !connected ? "Waiting for connection…" : messages.some((m) => m.type === "AI_TEXT") ? "Ready for your answer" : "Preparing the question…"}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <AnimatePresence>
          {messages.map((msg) => (
            <ChatMessage key={msg.id} msg={msg} />
          ))}
        </AnimatePresence>

        {messages.length === 0 && <ChatEmpty connected={connected} />}

        <div ref={chatEndRef} />
      </div>
    </div>
  );
}
