// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { profileApi } from "@/api/profile/profile.api";

afterEach(() => vi.unstubAllGlobals());

const wire = {
  name: "Ada",
  surname: "Lovelace",
  phoneNumber: "+380671234567",
  linkedinUrl: "https://linkedin.com/in/ada",
  githubUrl: "",
  yearsOfExperience: 3,
  techStack: ["Go"],
  resume: "",
};

it("keeps the LinkedIn URL across a load and save round-trip", async () => {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(wire), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  const loaded = await profileApi.get("token");
  expect(loaded?.linkedInUrl).toBe("https://linkedin.com/in/ada");

  await profileApi.put(loaded!, "token");
  const init = (fetchMock.mock.calls[1] as unknown as [string, RequestInit])[1];
  expect(JSON.parse(init.body as string)).toMatchObject({ linkedinUrl: "https://linkedin.com/in/ada" });
});
