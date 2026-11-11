import { Clock, Hash } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatTime } from "../utils/format";
import { positionLabel } from "@/lib/interview-labels";

interface MetaBarProps {
  time: number;
  currentQuestion: number;
  totalQuestions: number;
  level: string;
  position: string;
}

export function MetaBar({
  time,
  currentQuestion,
  totalQuestions,
  level,
  position,
}: MetaBarProps) {
  return (
    <div className="glass rounded-xl px-5 py-3 flex items-center flex-wrap gap-x-6 gap-y-2 text-sm">
      <div className="flex items-center gap-2 sm:hidden">
        <Clock className="w-3.5 h-3.5 text-primary" />
        <span className="text-muted-foreground">{formatTime(time)}</span>
      </div>
      <div className="flex items-center gap-2">
        <Hash className="w-3.5 h-3.5 text-primary" />
        <span className="text-muted-foreground">
          Question {currentQuestion || "—"}/{totalQuestions || "—"}
        </span>
      </div>
      <Badge className="bg-primary/15 text-primary border-primary/25 text-xs capitalize">
        {level}
      </Badge>
      <Badge
        variant="outline"
        className="border-border/40 text-muted-foreground text-xs capitalize"
      >
        {positionLabel(position)}
      </Badge>
    </div>
  );
}
