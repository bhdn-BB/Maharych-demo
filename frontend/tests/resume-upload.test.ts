// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { profileApi } from "@/api/profile/profile.api";

afterEach(() => vi.unstubAllGlobals());

it("reports upload progress separately from server extraction", async () => {
  class Request {
    upload = { onprogress: null as null | ((event: { lengthComputable: boolean; loaded: number; total: number }) => void), onload: null as null | (() => void) };
    onload: null | (() => void) = null;
    status = 200;
    responseText = JSON.stringify({ text: "Extracted resume" });
    open = vi.fn();
    setRequestHeader = vi.fn();
    send() {
      this.upload.onprogress?.({ lengthComputable: true, loaded: 1, total: 2 });
      this.upload.onload?.();
      this.onload?.();
    }
  }
  vi.stubGlobal("XMLHttpRequest", Request);
  const progress = vi.fn();
  const text = await profileApi.parseResume(new File(["data"], "resume.pdf"), "token", progress);
  expect(text).toBe("Extracted resume");
  expect(progress.mock.calls).toEqual([[50], [null]]);
});
