"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { Download, Loader2 } from "lucide-react";
import { useInterview, useInterviewFeedback } from "@/hooks/use-interview";
import { useBackendToken } from "@/hooks/use-backend-token";
import { interviewsApi } from "@/api/interviews/interviews.api";
import { positionLabel } from "@/lib/interview-labels";

export default function InterviewResultPage() {
  const { id } = useParams<{ id: string }>();
  const interview = useInterview(id);
  const status = interview.data?.status;
  // The report only exists after the asynchronous finalization finished.
  const feedback = useInterviewFeedback(id, status !== "finalizing");
  const report = feedback.data;
  const token = useBackendToken();
  const [downloadState, setDownloadState] = useState<
    "idle" | "loading" | "pending" | "error"
  >("idle");

  async function downloadPDF() {
    setDownloadState("loading");
    try {
      const blob = await interviewsApi.getReportPDF(id, token);
      if (!blob) {
        setDownloadState("pending");
        return;
      }
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `interview-${id}.pdf`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setDownloadState("idle");
    } catch {
      setDownloadState("error");
    }
  }

  if (interview.isLoading || feedback.isLoading) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }
  if (interview.isError || !interview.data) {
    return (
      <div className="min-h-screen gradient-bg flex flex-col items-center justify-center gap-4 p-8 text-center">
        <p>Interview not found.</p>
        <Link href="/dashboard" className="text-primary underline">
          Back to my interviews
        </Link>
      </div>
    );
  }
  if (status === "finalizing") {
    return (
      <div
        role="status"
        className="min-h-screen gradient-bg flex flex-col items-center justify-center gap-3 p-8 text-center"
      >
        <Loader2 className="h-8 w-8 animate-spin" />
        <p>Preparing your result… this usually takes a few seconds.</p>
      </div>
    );
  }
  if (status === "abandoned") {
    return (
      <main className="min-h-screen gradient-bg flex flex-col items-center justify-center gap-4 p-8 text-center">
        <h1 className="text-2xl font-semibold">No report for this interview</h1>
        <p className="max-w-xl text-muted-foreground">
          A report and PDF are created only when at least one answer was evaluated. This interview
          ended without an evaluated answer — no recording reached the interviewer, or the AI
          service was unavailable while answers were sent.
        </p>
        <Link href="/dashboard" className="text-primary underline">
          Start a new interview
        </Link>
      </main>
    );
  }
  if (status === "in_progress") {
    return (
      <div className="min-h-screen gradient-bg p-8 text-center">
        <p role="alert">
          Finishing this interview did not complete. Please try again.
        </p>
        <Link
          href={`/interview/${id}`}
          className="mt-3 inline-block text-primary underline"
        >
          Back to the interview
        </Link>
      </div>
    );
  }

  return (
    <main className="min-h-screen gradient-bg px-4 py-12">
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <Link
            href="/dashboard"
            className="text-sm text-primary hover:underline"
          >
            ← My interviews
          </Link>
          <h1 className="mt-3 text-3xl font-semibold">Interview result</h1>
          <p className="text-muted-foreground">
            {positionLabel(interview.data.position)} · {interview.data.level}
          </p>
          {report && (
            <div className="mt-3">
              <button
                type="button"
                onClick={downloadPDF}
                disabled={downloadState === "loading"}
                className="inline-flex items-center gap-2 rounded-xl border border-primary/30 px-4 py-2 text-sm font-medium text-primary hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
              >
                {downloadState === "loading" ? (
                  <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
                ) : (
                  <Download aria-hidden="true" className="h-4 w-4" />
                )}
                {downloadState === "loading"
                  ? "Preparing download…"
                  : "Download PDF report"}
              </button>
              {downloadState === "pending" && (
                <p className="text-sm text-muted-foreground">
                  The PDF is still being prepared. Try again shortly.
                </p>
              )}
              {downloadState === "error" && (
                <p role="alert" className="text-sm">
                  The PDF could not be downloaded. Please try again.
                </p>
              )}
            </div>
          )}
        </div>
        {feedback.isError ? (
          <p role="alert">
            The report could not be loaded. Please try again later.
          </p>
        ) : !report ? (
          <p>This interview ended before a final assessment was generated.</p>
        ) : (
          <>
            <section className="rounded-xl border bg-card p-6">
              <p className="text-sm text-muted-foreground">Overall score</p>
              <p className="text-4xl font-semibold">
                {report.overall_score}/{report.score_scale || 10}
              </p>
              <p className="mt-2">
                <span className="font-medium">Recommendation:</span>{" "}
                <span className="inline-block first-letter:uppercase">
                  {report.recommendation}
                </span>
              </p>
              <p className="mt-4">{report.summary}</p>
            </section>
            <div className="grid gap-4 sm:grid-cols-2">
              <section className="rounded-xl border bg-card p-6">
                <h2 className="font-semibold">Strengths</h2>
                <ul className="mt-3 list-disc pl-5 text-sm">
                  {report.top_strengths.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
              <section className="rounded-xl border bg-card p-6">
                <h2 className="font-semibold">Areas to improve</h2>
                <ul className="mt-3 list-disc pl-5 text-sm">
                  {report.top_weaknesses.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            </div>
            <section className="rounded-xl border bg-card p-6">
              <h2 className="font-semibold">Questions</h2>
              {report.partial && (
                <p className="mt-2 text-sm">
                  Partial interview: the score covers answered questions only.
                </p>
              )}
              {report.questions?.map((item) => (
                <article
                  key={item.question_id}
                  className="mt-4 rounded border p-4"
                >
                  <h3 className="font-medium">
                    {item.topic_index}. {item.question}
                    {item.clarification ? " (follow-up)" : ""}
                  </h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm">
                    {item.skipped
                      ? "No answer — question skipped."
                      : item.answer}
                  </p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {item.comment}
                  </p>
                </article>
              ))}
              <div className="mt-4 space-y-4">
                {report.topic_scores.map((topic) => (
                  <div
                    key={`${topic.topic_index}-${topic.question_type}`}
                    className="border-t pt-4 first:border-0 first:pt-0"
                  >
                    <p className="font-medium">
                      Question {topic.topic_index} · {topic.score}/
                      {report.score_scale || 10}
                    </p>
                    <div
                      role="meter"
                      aria-label={`Question ${topic.topic_index} score`}
                      aria-valuemin={0}
                      aria-valuemax={report.score_scale || 10}
                      aria-valuenow={topic.score}
                      className="mt-2 h-2 overflow-hidden rounded-full bg-muted"
                    >
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{
                          width: `${(Math.max(0, Math.min(report.score_scale || 10, topic.score)) / (report.score_scale || 10)) * 100}%`,
                        }}
                      />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {topic.comment}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
