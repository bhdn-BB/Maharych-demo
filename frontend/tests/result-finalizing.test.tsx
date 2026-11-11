// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import InterviewResultPage from "@/app/interview/[id]/result/page";

const mocks = vi.hoisted(() => ({
  interview: vi.fn(),
  feedback: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "iv-1" }) }));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));
vi.mock("@/hooks/use-backend-token", () => ({ useBackendToken: () => "token" }));
vi.mock("@/api/interviews/interviews.api", () => ({ interviewsApi: { getReportPDF: vi.fn() } }));
vi.mock("@/hooks/use-interview", () => ({
  useInterview: () => mocks.interview(),
  useInterviewFeedback: (id: string, ready: boolean) => mocks.feedback(id, ready),
}));

const interview = (status: string) => ({
  isLoading: false,
  isError: false,
  data: { id: "iv-1", status, position: "backend", level: "middle" },
});

afterEach(cleanup);

beforeEach(() => {
  mocks.feedback.mockReset();
  mocks.feedback.mockReturnValue({ isLoading: false, isError: false, data: null });
});

it("shows a progress state and does not request the report while finalizing", () => {
  mocks.interview.mockReturnValue(interview("finalizing"));
  render(<InterviewResultPage />);
  expect(screen.getByRole("status").textContent).toContain("Preparing your result");
  expect(mocks.feedback).toHaveBeenCalledWith("iv-1", false);
});

it("requests the report once the interview reached a terminal status", () => {
  mocks.interview.mockReturnValue(interview("completed"));
  render(<InterviewResultPage />);
  expect(mocks.feedback).toHaveBeenCalledWith("iv-1", true);
  expect(screen.queryByRole("status")).toBeNull();
});

it("offers a way back when finalization failed and the interview reopened", () => {
  mocks.interview.mockReturnValue(interview("in_progress"));
  render(<InterviewResultPage />);
  expect(screen.getByRole("alert").textContent).toContain("did not complete");
  expect(screen.getByRole("link", { name: /back to the interview/i }).getAttribute("href")).toBe("/interview/iv-1");
});

it("explains why an abandoned interview has no report instead of reporting a load error", () => {
  mocks.interview.mockReturnValue(interview("abandoned"));
  mocks.feedback.mockReturnValue({ isLoading: false, isError: true, data: null });
  render(<InterviewResultPage />);
  expect(screen.getByRole("heading", { name: /no report for this interview/i })).toBeTruthy();
  expect(screen.queryByText(/could not be loaded/i)).toBeNull();
  expect(screen.getByRole("link", { name: /start a new interview/i }).getAttribute("href")).toBe("/dashboard");
});
