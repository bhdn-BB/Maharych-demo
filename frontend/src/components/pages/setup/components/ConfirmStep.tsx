interface ConfirmStepProps {
  level: string;
  position: string;
  focus: string;
  language: "" | "uk" | "en";
}

export function ConfirmStep({
  level,
  position,
  focus,
  language,
}: ConfirmStepProps) {
  return (
    <div className="space-y-4">
      {[
        ["Level", level],
        ["Position", position],
        ["Interview type", focus],
        ["Language", language === "uk" ? "Українська" : language === "en" ? "English" : "—"],
      ].map(([label, value]) => (
        <div key={label} className="glass rounded-xl p-4 flex gap-4">
          <span className="w-28 shrink-0 text-muted-foreground">{label}</span>
          <span>{value}</span>
        </div>
      ))}
      <p className="text-sm text-muted-foreground">
        Five oral questions with two adaptive follow-ups each. Questions appear
        as text and server-generated speech. Each question allows one recording of up to 2 minutes.
      </p>
      <p className="text-sm text-muted-foreground">
        Your recordings are sent to an external AI provider for transcription
        and evaluation. Recordings are not stored permanently; questions,
        transcripts and results are saved to your account. Your resume is
        optional.
      </p>
    </div>
  );
}
