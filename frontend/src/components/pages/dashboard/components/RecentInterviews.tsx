"use client";

import Link from "next/link";
import { useState } from "react";
import { useInterviewHistory } from "@/hooks/use-interview";
import { FileText, Play } from "lucide-react";
import { positionLabel } from "@/lib/interview-labels";

// What the candidate can do with each interview: the report is the result they look for.
const statusInfo: Record<string, { label: string; action?: string }> = {
  completed: { label: "Report ready", action: "View report & PDF" },
  finalizing: { label: "Preparing report…", action: "Open" },
  in_progress: { label: "In progress", action: "Continue interview" },
  abandoned: { label: "No report — no answer was evaluated" },
};

export function RecentInterviews() {
  const [page, setPage] = useState(1);
  const history = useInterviewHistory(page);

  if (history.isLoading) return <p className="text-sm text-muted-foreground">Loading interview history…</p>;
  if (history.isError) return <p role="alert" className="text-sm">Interview history is unavailable.</p>;
  if (!history.data?.items.length && page === 1) return <p className="text-sm text-muted-foreground">No interviews yet.</p>;

  return (
    <div className="space-y-4">
      <ul className="grid gap-3">
        {history.data?.items.map((item) => (
          <li key={item.id} className="rounded-xl border bg-card p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="font-medium">
                  {positionLabel(item.position)} · {item.level}
                </p>
                <p className="text-sm text-muted-foreground">
                  {new Date(item.startedAt).toLocaleDateString()} ·{" "}
                  {statusInfo[item.status]?.label ?? item.status.replaceAll("_", " ")}
                </p>
              </div>
              {statusInfo[item.status]?.action && (
                <Link
                  href={item.status === "in_progress" ? `/interview/${item.id}` : `/interview/${item.id}/result`}
                  className="inline-flex items-center gap-2 rounded-lg border border-primary/30 px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary/10"
                >
                  {item.status === "in_progress" ? (
                    <Play aria-hidden="true" className="h-4 w-4" />
                  ) : (
                    <FileText aria-hidden="true" className="h-4 w-4" />
                  )}
                  {statusInfo[item.status]?.action}
                </Link>
              )}
            </div>
          </li>
        ))}
      </ul>
      <div className="flex items-center gap-4 text-sm">
        <button type="button" disabled={page === 1} onClick={() => setPage(page - 1)} className="disabled:opacity-40">Previous</button>
        <span>Page {page}</span>
        <button type="button" disabled={!history.data || page * history.data.pageSize >= history.data.total} onClick={() => setPage(page + 1)} className="disabled:opacity-40">Next</button>
      </div>
    </div>
  );
}
