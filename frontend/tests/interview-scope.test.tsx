// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CameraPreview } from "@/components/pages/interview/components/CameraPreview";
import { interviewOptionsApi } from "@/api/interview-options/interview-options.api";
import { apiFetch } from "@/lib/fetch";
import { MetaBar } from "@/components/pages/interview/components/MetaBar";
import { positionLabel } from "@/lib/interview-labels";
import { SelectionBar } from "@/components/pages/dashboard/components/SelectionBar";
import { LanguageSection } from "@/components/pages/dashboard/components/LanguageSection";
import { LanguageStep } from "@/components/pages/setup/components/LanguageStep";

vi.mock("@/lib/fetch", () => ({ apiFetch: vi.fn() }));
afterEach(cleanup);

it("excludes retired modes even when an older API response is cached", async () => {
  const option = (key: string) => ({
    key,
    label: key,
    category: "focus",
    id: 1,
    icon: "Code",
    sortOrder: 0,
  });
  const options = {
    levels: [{ ...option("middle"), category: "level" }],
    positions: [{ ...option("frontend"), category: "position" }],
    focuses: [
      "algorithms",
      "system-design",
      "behavioral",
      "live-coding",
      "unknown",
    ].map(option),
  };
  vi.mocked(apiFetch).mockResolvedValue(new Response(JSON.stringify(options)));
  const actual = await interviewOptionsApi.getAll();
  expect(actual.focuses.map((item) => item.key)).toEqual([
    "algorithms",
    "system-design",
    "behavioral",
  ]);
  expect(actual.levels).toEqual(options.levels);
  expect(actual.positions).toEqual(options.positions);
});

it("offers only the voice recording control in the answer panel", () => {
  const onMicToggle = vi.fn();
  const { rerender } = render(
    <CameraPreview micOn={false} canRecord onMicToggle={onMicToggle} />,
  );
  expect(screen.getAllByRole("button")).toHaveLength(1);
  screen.getByRole("button", { name: "Record answer" }).click();
  expect(onMicToggle).toHaveBeenCalledOnce();
  expect(screen.queryByText("Camera Preview")).toBeNull();
  rerender(<CameraPreview micOn canRecord onMicToggle={onMicToggle} />);
  screen.getByRole("button", { name: "Stop and send answer" });
});

it("displays the full Data Science position for saved interviews", () => {
  render(<MetaBar time={0} currentQuestion={1} totalQuestions={3} level="middle" position="data" />);
  expect(screen.getByText("Data Science")).toBeTruthy();
  expect(positionLabel("frontend")).toBe("Frontend");
  expect(positionLabel("other role")).toBe("other role");
});

it("shows full labels and lets the candidate select the interview language", () => {
  const onLanguageChange = vi.fn();
  render(<><LanguageSection selected="" onSelect={onLanguageChange} /><SelectionBar level="junior" position="data" focus="algorithms" language="" voice="Anna"
    onStart={vi.fn()} isPending={false} allSelected={false} visible /></>);
  expect(screen.getByText("Position: Data Science")).toBeTruthy();
  expect(screen.getByText("Type: Algorithms")).toBeTruthy();
  expect((screen.getByRole("button", { name: /Start Interview/ }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: /English/ }));
  expect(onLanguageChange).toHaveBeenCalledWith("en");
});

it("shows the chosen language as a selected setup option", () => {
  const onSelect = vi.fn();
  render(<LanguageStep selected="en" onSelect={onSelect} />);
  expect(screen.getByRole("button", { name: /English/ }).getAttribute("aria-pressed")).toBe("true");
  fireEvent.click(screen.getByRole("button", { name: /Українська/ }));
  expect(onSelect).toHaveBeenCalledWith("uk");
});
