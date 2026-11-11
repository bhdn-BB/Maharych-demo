export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

type ApiOptions = RequestInit & { token?: string };
type ApiVersion = "v1";

const Client = (basePath: string, version: ApiVersion) => {
  return async (url: string, options: ApiOptions = {}): Promise<Response> => {
    const { headers = {}, token, ...rest } = options;
    const input = new URL(`/api/${version}${url}`, basePath).href;
    const contentType =
      new Headers(headers).get("Content-Type") ?? "application/json";

    return fetch(input, {
      headers: {
        "Content-Type": contentType,
        ...(token && { Authorization: `Bearer ${token}` }),
        ...headers,
      },
      ...rest,
    });
  };
};

// NextAuth requests run on the server and use the Docker-internal API address.
const apiBaseURL =
  typeof window === "undefined"
    ? process.env.BACKEND_URL || BACKEND_URL
    : BACKEND_URL;
export const apiFetch = Client(apiBaseURL, "v1");
