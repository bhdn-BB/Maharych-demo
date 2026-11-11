import { CircleAlert } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
        <CircleAlert className="w-8 h-8 text-muted-foreground" />
      </div>
      <h3 className="font-display text-xl font-semibold mb-2">
        Interview options are unavailable
      </h3>
      <p className="text-muted-foreground">Please refresh the page or try again later.</p>
    </div>
  );
}
