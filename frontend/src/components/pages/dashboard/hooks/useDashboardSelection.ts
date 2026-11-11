import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useStartInterview } from "@/hooks/use-interview";
import { isSupportedInterviewFocus } from "@/lib/interview-focus";
import { useBackendToken } from "@/hooks/use-backend-token";
import { profileApi } from "@/api/profile/profile.api";
import type { VoiceId } from "../../setup/components/VoiceSelector";
import type {
  InterviewOptions,
} from "@/api/interview-options/interview-options.types";

export function useDashboardSelection(options: InterviewOptions) {
  const router = useRouter();
  const [level, setLevel] = useState("");
  const [position, setPosition] = useState("");
  const [focus, setFocus] = useState("");
  const [language, setLanguage] = useState<"" | "uk" | "en">("");
  const [voice, setVoice] = useState<VoiceId>("anna");
  const [checkingProfile, setCheckingProfile] = useState(false);
  const token = useBackendToken();

  const startInterview = useStartInterview();

  const filteredOptions = useMemo(() => {
    return {
      levels: options.levels,
      positions: options.positions,
      focuses: options.focuses.filter(
        (item) => isSupportedInterviewFocus(item.key),
      ),
    };
  }, [options]);

  const allSelected = !!level && !!position && !!focus && !!language;
  const hasAnySelection = !!level || !!position || !!focus || !!language;

  const hasResults =
    filteredOptions.levels.length > 0 ||
    filteredOptions.positions.length > 0 ||
    filteredOptions.focuses.length > 0;

  const handleStart = async () => {
    if (!allSelected || checkingProfile || startInterview.isPending) return;
    if (!token) {
      toast.error("Your session is not ready. Please sign in again.");
      return;
    }
    setCheckingProfile(true);
    try {
      const profile = await profileApi.get(token);
      if (!profile) {
        toast.info("Complete your profile before starting your interview.");
        router.push("/profile");
        return;
      }
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Could not load your profile.",
      );
      return;
    } finally {
      setCheckingProfile(false);
    }
    startInterview.mutate(
      { level, position, focus, language: language || undefined, voiceId: voice },
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
    filteredOptions,
    allSelected,
    hasAnySelection,
    hasResults,
    handleStart,
    isPending: checkingProfile || startInterview.isPending,
  };
}
