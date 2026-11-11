interface ChatEmptyProps {
  connected: boolean;
}

export function ChatEmpty({ connected }: ChatEmptyProps) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <div className="w-3 h-3 rounded-full bg-primary/60 mx-auto mb-3 animate-pulse" />
        <p className="text-xs text-muted-foreground">
          {connected ? "AI is preparing..." : "Connecting to AI..."}
        </p>
      </div>
    </div>
  );
}
