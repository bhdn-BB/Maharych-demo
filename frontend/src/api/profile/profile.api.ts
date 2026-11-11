import { apiFetch, BACKEND_URL } from "@/lib/fetch";
import type { CandidateProfile } from "./profile.types";

async function readResponse(res: Response): Promise<CandidateProfile> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || "Profile request failed");
  }
  return fromWire(await res.json());
}

// The Go API uses `linkedinUrl` on the wire; the UI model uses `linkedInUrl`.
type WireProfile = Omit<CandidateProfile, "linkedInUrl"> & { linkedinUrl?: string; linkedInUrl?: string };

function fromWire(body: WireProfile): CandidateProfile {
  const { linkedinUrl, linkedInUrl, ...rest } = body;
  return {
    ...rest,
    linkedInUrl: linkedInUrl ?? linkedinUrl ?? "",
    githubUrl: rest.githubUrl ?? "",
    techStack: rest.techStack ?? [],
    resume: rest.resume ?? "",
  };
}

function toWire({ linkedInUrl, ...rest }: CandidateProfile) {
  return { ...rest, linkedinUrl: linkedInUrl };
}

export const profileApi = {
  parseResume: async (
    file: File,
    token: string,
    onProgress?: (percent: number | null) => void,
    signal?: AbortSignal,
  ): Promise<string> => {
    const kind = file.name.split(".").pop()?.toLowerCase();
    if (kind !== "pdf" && kind !== "docx") throw new Error("Choose a PDF or DOCX file.");
    if (!file.size || file.size > 5 * 1024 * 1024) throw new Error("Choose a file smaller than 5 MiB.");
    return new Promise((resolve, reject) => {
      const request = new XMLHttpRequest();
      request.open("POST", new URL(`/api/v1/profile/resume/parse?kind=${kind}`, BACKEND_URL));
      request.setRequestHeader("Authorization", `Bearer ${token}`);
      request.setRequestHeader("Content-Type", "application/octet-stream");
      request.timeout = 60000;
      request.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress?.(Math.round(event.loaded * 100 / event.total));
      };
      request.upload.onload = () => onProgress?.(null);
      request.onerror = () => reject(new Error("Could not upload the resume. Check your connection and try again."));
      request.ontimeout = () => reject(new Error("Resume processing took too long. Please try again."));
      request.onabort = () => reject(new Error("Resume upload was cancelled."));
      request.onload = () => {
        let body: { text?: string; error?: string; detail?: string } = {};
        try { body = JSON.parse(request.responseText); } catch { /* handled below */ }
        if (request.status < 200 || request.status >= 300 || typeof body.text !== "string") {
          reject(new Error(body.detail || body.error || "Could not read the resume."));
        } else {
          resolve(body.text);
        }
      };
      if (signal?.aborted) { reject(new Error("Resume upload was cancelled.")); return; }
      signal?.addEventListener("abort", () => request.abort(), { once: true });
      request.send(file);
    });
  },
  get: async (token: string): Promise<CandidateProfile | null> => {
    const res = await apiFetch("/profile", { token });
    if (res.status === 404) return null;
    return readResponse(res);
  },
  put: async (profile: CandidateProfile, token: string): Promise<CandidateProfile> =>
    readResponse(
      await apiFetch("/profile", {
        method: "PUT",
        token,
        body: JSON.stringify(toWire(profile)),
      }),
    ),
};
