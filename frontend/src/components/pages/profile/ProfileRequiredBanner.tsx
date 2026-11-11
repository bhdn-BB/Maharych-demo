"use client";

import Link from "next/link";
import { ArrowRight, UserRoundPen } from "lucide-react";
import { useProfile } from "@/hooks/use-profile";

/** Tells the candidate up front that a profile is required, before they pick options. */
export function ProfileRequiredBanner({ className = "" }: { className?: string }) {
  const profile = useProfile();
  if (profile.data !== null) return null;
  return (
    <div
      role="status"
      className={`flex flex-col gap-3 rounded-2xl border border-primary/30 bg-primary/10 p-4 sm:flex-row sm:items-center sm:justify-between ${className}`}
    >
      <div className="flex items-start gap-3">
        <UserRoundPen aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
        <p className="text-sm">
          <span className="font-semibold">Complete your profile first.</span>{" "}
          <span className="text-muted-foreground">
            It takes a minute and lets the interviewer tailor questions to your experience.
          </span>
        </p>
      </div>
      <Link
        href="/profile"
        className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        Fill in profile <ArrowRight aria-hidden="true" className="h-4 w-4" />
      </Link>
    </div>
  );
}
