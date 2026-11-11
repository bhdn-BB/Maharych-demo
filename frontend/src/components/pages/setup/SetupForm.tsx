"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSetupWizard, STEP_LABELS } from "./hooks/useSetupWizard";
import { StepProgress } from "./components/StepProgress";
import { LevelStep } from "./components/LevelStep";
import { PositionStep } from "./components/PositionStep";
import { FocusStep } from "./components/FocusStep";
import { LanguageStep } from "./components/LanguageStep";
import { ConfirmStep } from "./components/ConfirmStep";
import { VoiceSelector } from "./components/VoiceSelector";
import { slideVariants } from "./utils/animations";
import type { SetupFormProps } from "./types/setup.types";
import { isSupportedInterviewFocus } from "@/lib/interview-focus";
import { ProfileRequiredBanner } from "../profile/ProfileRequiredBanner";

export function SetupForm({ options }: SetupFormProps) {
  const {
    step,
    dir,
    totalSteps,
    level,
    setLevel,
    position,
    setPosition,
    focus,
    setFocus,
    language,
    setLanguage,
    voice,
    setVoice,
    next,
    prev,
    canNext,
    handleStart,
    isPending,
  } = useSetupWizard();

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center px-4 py-10">
      {/* Ambient glow */}
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-primary/8 blur-[100px] pointer-events-none" />

      <div className="w-full max-w-2xl">
        <ProfileRequiredBanner className="mb-6" />
        <StepProgress
          labels={STEP_LABELS}
          currentStep={step}
          totalSteps={totalSteps}
        />

        <div className="glass rounded-3xl p-8 md:p-12 glow-border min-h-[420px] flex flex-col">
          <AnimatePresence mode="wait" custom={dir}>
            <motion.div
              key={step}
              custom={dir}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="flex-1"
            >
              <h2 className="font-display text-2xl md:text-3xl font-bold text-center mb-8">
                {STEP_LABELS[step]}
              </h2>

              {step === 0 && (
                <LevelStep
                  levels={options.levels}
                  selected={level}
                  onSelect={setLevel}
                />
              )}

              {step === 1 && (
                <PositionStep
                  positions={options.positions}
                  selected={position}
                  onSelect={setPosition}
                />
              )}

              {step === 2 && (
                <FocusStep
                  focuses={options.focuses.filter((item) =>
                    isSupportedInterviewFocus(item.key),
                  )}
                  selected={focus}
                  onSelect={setFocus}
                />
              )}

              {step === 3 && (
                <LanguageStep selected={language} onSelect={setLanguage} />
              )}

              {step === 4 && (
                <div className="space-y-8"><ConfirmStep
                  level={level}
                  position={options.positions.find((item) => item.key === position)?.label ?? position}
                  focus={options.focuses.find((item) => item.key === focus)?.label ?? focus}
                  language={language}
                /><VoiceSelector value={voice} onChange={setVoice} language={language} /></div>
              )}
            </motion.div>
          </AnimatePresence>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-border/20">
            <Button
              variant="ghost"
              onClick={prev}
              disabled={step === 0}
              className="text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>

            {step < totalSteps - 1 ? (
              <Button
                onClick={next}
                disabled={!canNext()}
                className="bg-primary hover:bg-primary/90 text-primary-foreground glow-button"
              >
                Next
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            ) : (
              <Button
                onClick={handleStart}
                disabled={isPending || !language}
                className="bg-primary hover:bg-primary/90 text-primary-foreground glow-button"
              >
                {isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : null}
                Start Interview
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
