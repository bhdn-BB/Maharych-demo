"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Loader2, RotateCcw, Square } from "lucide-react";
import { useInterviewSession } from "./hooks/useInterviewSession";
import { InterviewHeader } from "./components/InterviewHeader";
import { CameraPreview } from "./components/CameraPreview";
import { MetaBar } from "./components/MetaBar";
import { ChatPanel } from "./components/ChatPanel";
import { Button } from "@/components/ui/button";

export function InterviewPage() {
  const params = useParams();
  const interviewId = params.id as string;

  const {
    interview,
    reconnect,
    replayAudio,
    stopAudio,
    recordingSeconds,
    streamError,
    isLoading,
    isInProgress,
    time,
    micOn,
    canRecord,
    processing,
    waitingForQuestion,
    questionPlaying,
    handleMicToggle,
    connected,
    messages,
    currentQuestion,
    totalQuestions,
    chatEndRef,
    handleEnd,
    isEnding,
    clockPaused,
  } = useInterviewSession(interviewId);

  if (isLoading) {
    return (
      <div className="h-screen gradient-bg flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!interview) {
    return (
      <div className="h-screen gradient-bg flex flex-col items-center justify-center gap-4">
        <p className="text-muted-foreground">Interview not found</p>
        <Button asChild variant="outline">
          <Link href="/dashboard">Back to my interviews</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="h-screen gradient-bg flex flex-col overflow-hidden">
      <InterviewHeader
        isInProgress={isInProgress}
        connected={connected}
        time={time}
        clockPaused={clockPaused}
        onEnd={handleEnd}
        isEnding={isEnding || processing || micOn}
      />

      <div className="flex flex-wrap items-center gap-3 px-4 py-2 text-sm">
        <Button variant="outline" size="sm"
          disabled={!connected || micOn}
          onClick={replayAudio}
          className="border-primary/30 hover:bg-primary/10"
        >
          <RotateCcw aria-hidden="true" className="w-4 h-4" />
          Replay question
        </Button>
        <Button variant="outline" size="sm" disabled={!connected || !questionPlaying} onClick={stopAudio} className="border-primary/30 hover:bg-primary/10">
          <Square aria-hidden="true" className="w-3.5 h-3.5 fill-current" />
          Stop audio
        </Button>
        {(!connected || !!streamError) && (
          <Button variant="outline" size="sm" onClick={reconnect} className="border-primary/30 hover:bg-primary/10">
            Reconnect
          </Button>
        )}
        {micOn && <span>Recording: {recordingSeconds}/120 s</span>}
        {streamError && <span role="alert">{streamError}</span>}
      </div>
      {/* Main content */}
      <div className="flex-1 flex flex-col md:flex-row gap-3 p-3 min-h-0 overflow-y-auto">
        {/* Voice answer area - 2/3 */}
        <div className="flex-[2] flex flex-col gap-3 min-w-0">
          <CameraPreview
            micOn={micOn}
            onMicToggle={handleMicToggle}
            canRecord={canRecord}
            status={
              streamError && !micOn && !processing
                ? "error"
                : !connected
                ? "connecting"
                : questionPlaying
                  ? "speaking"
                  : waitingForQuestion || currentQuestion === 0
                    ? "preparing"
                  : processing
                    ? "evaluating"
                    : "ready"
            }
          />
          <MetaBar
            time={time}
            currentQuestion={currentQuestion}
            totalQuestions={totalQuestions}
            level={interview.level}
            position={interview.position}
          />
        </div>

        {/* AI Chat panel - 1/3 */}
        <ChatPanel
          connected={connected}
          processing={processing}
          waitingForQuestion={waitingForQuestion && !questionPlaying}
          questionPlaying={questionPlaying}
          messages={messages}
          chatEndRef={chatEndRef}
        />
      </div>
    </div>
  );
}
