import { Loader2, Mic, Square } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CameraPreviewProps {
  micOn: boolean;
  onMicToggle: () => void;
  canRecord: boolean;
  status?: "connecting" | "preparing" | "speaking" | "evaluating" | "ready" | "error";
}

const statusText = {
  connecting: "Connecting to the interviewer…",
  preparing: "The interviewer is preparing the question…",
  speaking: "The interviewer is reading the question. Recording unlocks when it ends — or press Stop audio.",
  evaluating: "Evaluating your answer…",
  ready: "One recording per question · up to 2 minutes",
  error: "Something went wrong. Press Reconnect to continue.",
};

export function CameraPreview({
  micOn,
  onMicToggle,
  canRecord,
  status = "ready",
}: CameraPreviewProps) {
  const busy = !micOn && status !== "ready" && status !== "error" && status !== "speaking";
  const speaking = !micOn && status === "speaking";
  return (
    <div className="flex-1 glass rounded-2xl relative overflow-hidden flex items-center justify-center glow-border">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent" />
      <div className="text-center z-10">
        <div className="w-20 h-20 rounded-full bg-muted/30 flex items-center justify-center mx-auto mb-4">
          {busy ? (
            <Loader2 aria-hidden="true" className="w-8 h-8 animate-spin text-primary" />
          ) : (
            <Mic aria-hidden="true" className={`w-8 h-8 ${micOn ? "text-destructive animate-pulse" : "text-muted-foreground"}`} />
          )}
        </div>
        <p className="text-muted-foreground text-sm">Voice answer</p>
        <p role="status" aria-live="polite" className="text-xs text-muted-foreground mt-2">
          {micOn
            ? "Recording answer — press the red button to send"
            : speaking
              ? statusText.speaking
              : busy || status === "error"
                ? `${statusText[status]} The clock is paused.`
              : statusText.ready}
        </p>
      </div>

      {/* Controls overlay */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2">
        <Button
          size="icon"
          variant="ghost"
          onClick={onMicToggle}
          disabled={!micOn && !canRecord}
          aria-label={micOn ? "Stop and send answer" : "Record answer"}
          className={`rounded-full w-14 h-14 focus-visible:ring-2 focus-visible:ring-primary ${micOn ? "bg-destructive text-white hover:bg-destructive/80" : "bg-primary text-primary-foreground glow-button hover:bg-primary/90"}`}
        >
          {micOn ? <Square className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
        </Button>
      </div>
    </div>
  );
}
