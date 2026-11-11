"use client";

import { DashboardHero } from "./components/DashboardHero";
import { CategorySection } from "./components/CategorySection";
import { SelectionBar } from "./components/SelectionBar";
import { EmptyState } from "./components/EmptyState";
import { RecentInterviews } from "./components/RecentInterviews";
import { LanguageSection } from "./components/LanguageSection";
import { useDashboardSelection } from "./hooks/useDashboardSelection";
import type { DashboardPageProps } from "./types/dashboard.types";
import { VoiceSelector, voices } from "../setup/components/VoiceSelector";
import { ProfileRequiredBanner } from "../profile/ProfileRequiredBanner";

export function DashboardPage({ options }: DashboardPageProps) {
  const {
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
    isPending,
  } = useDashboardSelection(options);

  return (
    <div className="min-h-screen gradient-bg">
      {/* Ambient glow */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full bg-primary/8 blur-[150px] pointer-events-none" />

      <DashboardHero />
      <div className="mx-auto max-w-5xl px-6">
        <ProfileRequiredBanner className="mb-6" />
      </div>

      {hasResults ? (
        <>
          <CategorySection
            title="Experience Level"
            highlight="Level"
            subtitle="Select the difficulty that matches your experience"
            items={filteredOptions.levels}
            selectedKey={level}
            onSelect={setLevel}
          />
          <CategorySection
            title="Target Position"
            highlight="Position"
            subtitle="Choose the role you're preparing for"
            items={filteredOptions.positions}
            selectedKey={position}
            onSelect={setPosition}
          />
          <CategorySection
            title="Interview Type"
            highlight="Type"
            subtitle="Choose the kind of interview you want to practice"
            items={filteredOptions.focuses}
            selectedKey={focus}
            onSelect={setFocus}
          />
        </>
      ) : (
        <EmptyState />
      )}

      <LanguageSection selected={language} onSelect={setLanguage} />
      <section className="mx-auto max-w-5xl px-6 py-8">
        <VoiceSelector value={voice} onChange={setVoice} language={language} />
      </section>

      {/* Spacer for fixed bottom bar */}
      {hasAnySelection && <div className="h-44 sm:h-24" />}

      <SelectionBar
        level={level}
        position={options.positions.find((item) => item.key === position)?.label ?? position}
        focus={options.focuses.find((item) => item.key === focus)?.label ?? focus}
        language={language}
        voice={voices.find((item) => item.id === voice)?.name ?? voice}
        onStart={handleStart}
        isPending={isPending}
        allSelected={allSelected}
        visible={hasAnySelection}
      />

      <section className="mx-auto max-w-5xl px-4 py-10">
        <h2 className="mb-4 text-2xl font-semibold">Recent interviews</h2>
        <RecentInterviews />
      </section>
    </div>
  );
}
