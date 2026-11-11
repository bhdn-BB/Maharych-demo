import { motion } from "framer-motion";
import Markdown from "react-markdown";
import type { AudioStreamMessage } from "@/hooks/use-audio-stream";

interface ChatMessageProps {
  msg: AudioStreamMessage;
}

export function ChatMessage({ msg }: ChatMessageProps) {
  const content = msg.transcription || msg.text || msg.stage || "";

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`glass rounded-xl p-3.5 ${
        msg.type === "TRANSCRIPTION"
          ? "border-muted/20 ml-4"
          : msg.type === "STAGE_UPDATE"
            ? "border-primary/20 bg-primary/5"
            : "border-primary/10"
      }`}
    >
      {msg.type === "TRANSCRIPTION" && (
        <p className="text-xs text-muted-foreground mb-1">You</p>
      )}
      {msg.type === "AI_TEXT" && (
        <p className="text-xs text-primary mb-1">AI</p>
      )}
      {msg.type === "STAGE_UPDATE" && (
        <p className="text-xs text-primary mb-1">Stage: {msg.stage}</p>
      )}
      {msg.type === "AI_TEXT" ? (
        <div className="prose prose-sm prose-invert max-w-none prose-p:leading-relaxed prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-pre:my-2 prose-pre:bg-black/30 prose-pre:rounded-lg prose-code:text-primary prose-code:before:content-none prose-code:after:content-none prose-a:text-primary prose-strong:text-foreground">
          <Markdown>{content}</Markdown>
        </div>
      ) : (
        <p className="text-sm leading-relaxed">{content}</p>
      )}
    </motion.div>
  );
}
