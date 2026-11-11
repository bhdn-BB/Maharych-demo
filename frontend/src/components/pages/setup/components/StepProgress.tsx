interface StepProgressProps {
  labels: string[];
  currentStep: number;
  totalSteps: number;
}

export function StepProgress({
  labels,
  currentStep,
  totalSteps,
}: StepProgressProps) {
  return (
    <>
      <div aria-hidden="true" className="flex items-center justify-center gap-2 sm:gap-3 mb-8">
        {labels.map((l, i) => (
          <div key={l} className="flex items-center gap-2 sm:gap-3">
            <div
              className={`w-3 h-3 rounded-full transition-all duration-300 ${i <= currentStep ? "bg-primary scale-110" : "bg-muted"}`}
            />
            {i < labels.length - 1 && (
              <div
                className={`w-6 sm:w-12 h-0.5 transition-colors duration-300 ${i < currentStep ? "bg-primary/60" : "bg-muted"}`}
              />
            )}
          </div>
        ))}
      </div>

      <p className="text-center text-sm text-muted-foreground mb-2" aria-live="polite">
        Step {currentStep + 1} of {totalSteps}
        <span className="text-foreground/80"> · {labels[currentStep]}</span>
      </p>
    </>
  );
}
