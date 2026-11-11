import { Clock, LogOut, Loader2, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { formatTime } from "../utils/format";

interface InterviewHeaderProps {
  isInProgress: boolean;
  connected: boolean;
  time: number;
  clockPaused?: boolean;
  onEnd: () => void;
  isEnding: boolean;
}

export function InterviewHeader({
  isInProgress,
  connected,
  time,
  clockPaused = false,
  onEnd,
  isEnding,
}: InterviewHeaderProps) {
  return (
    <header className="glass-strong flex items-center justify-between gap-3 px-4 sm:px-6 py-3 z-10">
      <div className="flex items-center gap-4">
        <span className="hidden sm:inline font-display font-bold gradient-text">
          InterviewLeap
        </span>
        <Badge
          variant="outline"
          className="border-primary/30 text-primary text-xs"
        >
          {isInProgress ? "Live Session" : "Completed"}
        </Badge>
        {isInProgress && (
          <div className="flex items-center gap-1.5">
            {connected ? (
              <Wifi className="w-3.5 h-3.5 text-green-400" />
            ) : (
              <WifiOff className="w-3.5 h-3.5 text-muted-foreground" />
            )}
            <span className="text-xs text-muted-foreground">
              {connected ? "Connected" : "Connecting..."}
            </span>
          </div>
        )}
      </div>
      <div className="hidden sm:flex items-center gap-3 text-sm text-muted-foreground">
        <Clock aria-hidden="true" className="w-4 h-4 text-primary" />
        <span className={`font-mono ${clockPaused ? "opacity-60" : ""}`}>{formatTime(time)}</span>
        {clockPaused && (
          <span className="text-xs" title="The clock runs only while a question is on screen">
            paused
          </span>
        )}
      </div>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            disabled={isEnding || !isInProgress}
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            {isEnding ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <LogOut className="w-4 h-4 mr-2" />
            )}
            <span className="hidden sm:inline">End Interview</span>
            <span className="sm:hidden">End</span>
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>End the interview now?</AlertDialogTitle>
            <AlertDialogDescription>
              You can&apos;t resume it later. Questions you haven&apos;t answered
              yet will not be scored, and your result will be based on the
              answers given so far.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep going</AlertDialogCancel>
            <AlertDialogAction
              onClick={onEnd}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              End interview
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </header>
  );
}
