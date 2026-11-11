// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { useDashboardSelection } from "@/components/pages/dashboard/hooks/useDashboardSelection";

const mocks = vi.hoisted(() => ({ push: vi.fn(), mutate: vi.fn(), get: vi.fn(), info: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push }) }));
vi.mock("@/hooks/use-backend-token", () => ({ useBackendToken: () => "token" }));
vi.mock("@/hooks/use-interview", () => ({ useStartInterview: () => ({ mutate: mocks.mutate, isPending: false }) }));
vi.mock("@/api/profile/profile.api", () => ({ profileApi: { get: mocks.get } }));
vi.mock("sonner", () => ({ toast: { info: mocks.info, error: vi.fn() } }));

it("guides a candidate without a profile to complete it before starting", async () => {
  mocks.get.mockResolvedValue(null);
  const { result } = renderHook(() => useDashboardSelection({ levels: [], positions: [], focuses: [] }));
  act(() => {
    result.current.setLevel("junior");
    result.current.setPosition("data");
    result.current.setFocus("behavioral");
    result.current.setLanguage("uk");
  });
  await act(async () => { await result.current.handleStart(); });
  expect(mocks.push).toHaveBeenCalledWith("/profile");
  expect(mocks.mutate).not.toHaveBeenCalled();
});

it("passes the selected interview language and voice when starting", async () => {
  mocks.mutate.mockClear();
  mocks.get.mockResolvedValue({ name: "Candidate" });
  const { result } = renderHook(() => useDashboardSelection({ levels: [], positions: [], focuses: [] }));
  act(() => {
    result.current.setLevel("junior");
    result.current.setPosition("data");
    result.current.setFocus("behavioral");
    result.current.setLanguage("en");
    result.current.setVoice("daniel");
  });
  await act(async () => { await result.current.handleStart(); });
  expect(mocks.mutate).toHaveBeenCalledWith(
    { level: "junior", position: "data", focus: "behavioral", language: "en", voiceId: "daniel" },
    expect.any(Object),
  );
});
