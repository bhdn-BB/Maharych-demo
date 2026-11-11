import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { interviewTypeLabel, positionLabel } from "@/lib/interview-labels";

interface SelectionBarProps {
  level: string;
  position: string;
  focus: string;
  language: "" | "uk" | "en";
  voice: string;
  onStart: () => void;
  isPending: boolean;
  allSelected: boolean;
  visible: boolean;
}

export function SelectionBar({
  level,
  position,
  focus,
  language,
  voice,
  onStart,
  isPending,
  allSelected,
  visible,
}: SelectionBarProps) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="fixed bottom-0 left-0 right-0 z-40 glass-strong border-t border-border/30"
        >
          <div className="container mx-auto flex flex-col items-stretch justify-between py-3 px-4 gap-3 sm:flex-row sm:items-center sm:px-6">
            <div className="flex items-center gap-2 flex-wrap">
              <SelectionChip label="Level" value={level} />
              <SelectionChip label="Position" value={positionLabel(position)} />
              <SelectionChip label="Type" value={interviewTypeLabel(focus)} />
              <SelectionChip label="Language" value={language === "uk" ? "Українська" : language === "en" ? "English" : ""} />
              <SelectionChip label="Voice" value={voice} />
            </div>
            <Button
              onClick={onStart}
              disabled={!allSelected || isPending}
              className="glow-button bg-primary hover:bg-primary/90 text-primary-foreground font-semibold px-6 shrink-0 w-full sm:w-auto"
            >
              {isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <ArrowRight className="w-4 h-4 mr-2" />
              )}
              Start Interview
            </Button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function SelectionChip({ label, value }: { label: string; value: string }) {
  if (!value) {
    return (
      <Badge
        variant="outline"
        className="border-border/40 text-muted-foreground text-xs"
      >
        Pick {label.toLowerCase()}
      </Badge>
    );
  }

  return (
    <Badge
      variant="secondary"
      className="bg-primary/15 text-primary border border-primary/30 text-xs"
    >
      {label}: {value}
    </Badge>
  );
}
