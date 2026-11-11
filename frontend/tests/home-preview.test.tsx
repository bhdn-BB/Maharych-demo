// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { HomePage } from "@/components/pages/home/HomePage";

vi.mock("next-auth/react", () => ({ useSession: () => ({ data: null }) }));
vi.stubGlobal(
  "IntersectionObserver",
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
);
afterEach(cleanup);

it("updates the sample question and selected states for a level and role", () => {
  render(<HomePage />);
  fireEvent.click(screen.getByRole("button", { name: /Senior/ }));
  fireEvent.click(screen.getByRole("button", { name: "Backend" }));

  expect(
    screen.getByRole("button", { name: /Senior/ }).getAttribute("aria-pressed"),
  ).toBe("true");
  expect(
    screen
      .getByRole("button", { name: "Backend" })
      .getAttribute("aria-pressed"),
  ).toBe("true");
  expect(screen.getByText(/an API endpoint whose response time rises/)).toBeTruthy();
  expect(screen.getByText(/This is a preview/)).toBeTruthy();
});

it("switches the sample interview type on the first screen", () => {
  render(<HomePage />);
  const algorithms = screen.getByRole("button", { name: "Algorithms" });
  fireEvent.click(algorithms);
  expect(algorithms.getAttribute("aria-pressed")).toBe("true");
  expect(screen.getByText(/find the first duplicate/)).toBeTruthy();
});
