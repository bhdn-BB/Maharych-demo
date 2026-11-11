import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useStartInterview } from "@/hooks/use-interview";
import { useBackendToken } from "@/hooks/use-backend-token";
import { profileApi } from "@/api/profile/profile.api";
import type { VoiceId } from "../components/VoiceSelector";

const TOTAL_STEPS = 5;

export const STEP_LABELS = [
  "Experience Level",
  "Position",
  "Interview Type",
  "Interview Language",
  "Confirm & Start",
];

export function useSetupWizard() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [dir, setDir] = useState(1);
  const [level, setLevel] = useState("");
  const [position, setPosition] = useState("");
  const [focus, setFocus] = useState("");
  const [language, setLanguage] = useState<"" | "uk" | "en">("");
  const [voice, setVoice] = useState<VoiceId>("anna");
  const [checkingProfile, setCheckingProfile] = useState(false);
  const startInterview = useStartInterview();
  const token = useBackendToken();

  const next = () => {
    if (step < TOTAL_STEPS - 1) {
      setDir(1);
      setStep((s) => s + 1);
    }
  };

  const prev = () => {
    if (step > 0) {
      setDir(-1);
      setStep((s) => s - 1);
    }
  };

  const canNext = () => {
    if (step === 0) return !!level;
    if (step === 1) return !!position;
    if (step === 2) return !!focus;
    if (step === 3) return !!language;
    return true;
  };

  const handleStart = async () => {
    if (!language) { toast.error("Choose the interview language."); return; }
    if (checkingProfile || startInterview.isPending) return;
    if (!token) {
      toast.error("Your session is not ready. Please sign in again.");
      return;
    }

    setCheckingProfile(true);
    try {
      const candidateProfile = await profileApi.get(token);
      if (!candidateProfile) {
        toast.error("Complete your candidate profile before starting.");
        router.push("/profile");
        return;
      }
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Could not load your profile",
      );
      return;
    } finally {
      setCheckingProfile(false);
    }

    startInterview.mutate(
      { level, position, focus, language, voiceId: voice },
      {
        onSuccess: (data) => {
          router.push(`/interview/${data.id}`);
        },
        onError: (err) => {
          toast.error(err.message || "Failed to start interview");
        },
      },
    );
  };

  return {
    step,
    dir,
    totalSteps: TOTAL_STEPS,
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
    isPending: checkingProfile || startInterview.isPending,
  };
}
