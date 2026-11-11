import { BACKEND_URL, apiFetch } from "@/lib/fetch";

/** Build the WebSocket URL from a one-time ticket (never from the API JWT). */
export function getAudioStreamUrl(interviewId: string, ticket: string): string {
  const wsBase = BACKEND_URL.replace(/^http/, "ws");
  return `${wsBase}/api/v1/interviews/${interviewId}/audio?ticket=${encodeURIComponent(ticket)}`;
}

/** Exchange the session token for a 30-second, single-use WebSocket ticket. */
export async function requestAudioTicket(
  interviewId: string,
  token: string,
): Promise<string> {
  const res = await apiFetch(`/interviews/${interviewId}/audio-ticket`, {
    token,
    method: "POST",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || "Could not open the interview connection");
  }
  const data = (await res.json()) as { ticket?: string };
  if (!data.ticket) throw new Error("Could not open the interview connection");
  return data.ticket;
}
