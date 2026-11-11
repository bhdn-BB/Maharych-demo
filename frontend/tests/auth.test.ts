import { beforeEach, expect, it, vi } from "vitest";

type Callbacks = {
  authorized: (args: {
    auth?: { user?: object; backendToken?: string };
    request: { nextUrl: { pathname: string } };
  }) => boolean;
  jwt: (args: {
    token: Record<string, unknown>;
    account?: { provider: string; id_token?: string };
  }) => Promise<Record<string, unknown>>;
};
const captured = vi.hoisted(() => ({
  callbacks: null as unknown as Callbacks,
}));
vi.mock("next-auth", () => ({
  default: (config: { callbacks: Callbacks }) => {
    captured.callbacks = config.callbacks;
    return {};
  },
}));
vi.mock("next-auth/providers/credentials", () => ({
  default: (config: unknown) => config,
}));
vi.mock("next-auth/providers/google", () => ({
  default: (config: unknown) => config,
}));
vi.mock("@/lib/fetch", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "@/lib/fetch";
import "@/auth";

beforeEach(() => {
  vi.mocked(apiFetch).mockReset();
});

function apiToken(expiresAt = Math.floor(Date.now() / 1000) + 3600) {
  return (
    "test-header." +
    btoa(JSON.stringify({ exp: expiresAt })).replace(/=+$/, "") +
    ".test-signature"
  );
}

it("rejects a Google browser session when Go rejects the token exchange", async () => {
  vi.mocked(apiFetch).mockResolvedValue(new Response("{}", { status: 401 }));
  await expect(
    captured.callbacks.jwt({
      token: {},
      account: { provider: "google", id_token: "test-token" },
    }),
  ).rejects.toThrow("could not create an API session");
});

it("rejects a missing Google ID token and a network failure", async () => {
  await expect(
    captured.callbacks.jwt({ token: {}, account: { provider: "google" } }),
  ).rejects.toThrow("ID token");
  vi.mocked(apiFetch).mockImplementation(async () => {
    throw new Error("offline");
  });
  const failure = await captured.callbacks
    .jwt({
      token: {},
      account: { provider: "google", id_token: "test-token" },
    })
    .then(
      () => null,
      (error: Error) => error.message,
    );
  expect(failure).toBe("Google sign-in could not create an API session");
});

it("requires an API token on protected pages", () => {
  const request = { nextUrl: { pathname: "/interview/id" } };
  expect(captured.callbacks.authorized({ auth: { user: {} }, request })).toBe(
    false,
  );
  expect(
    captured.callbacks.authorized({
      auth: { user: {}, backendToken: "test-api-token" },
      request,
    }),
  ).toBe(true);
});

it("uses the account and token returned by Go after a successful Google exchange", async () => {
  const issued = apiToken();
  vi.mocked(apiFetch).mockResolvedValue(
    new Response(
      JSON.stringify({
        user: { id: 7, email: "test@example.com" },
        token: issued,
      }),
      { status: 200 },
    ),
  );
  const token = await captured.callbacks.jwt({
    token: {},
    account: { provider: "google", id_token: "test-token" },
  });
  expect(token).toMatchObject({ backendToken: issued, userId: "7" });
});

it("expires the API capability when Go's JWT expires", async () => {
  const token = await captured.callbacks.jwt({
    token: { backendToken: apiToken(1), userId: "7" },
  });
  expect(token.backendToken).toBeUndefined();
  expect(token.userId).toBeUndefined();
});

it("rejects a successful HTTP exchange that returns a malformed API token", async () => {
  vi.mocked(apiFetch).mockResolvedValue(
    new Response(JSON.stringify({ user: { id: 7 }, token: "malformed" }), {
      status: 200,
    }),
  );
  await expect(
    captured.callbacks.jwt({
      token: {},
      account: { provider: "google", id_token: "test-token" },
    }),
  ).rejects.toThrow("current API token");
});
