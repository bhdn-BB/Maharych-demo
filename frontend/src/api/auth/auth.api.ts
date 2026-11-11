import { apiFetch } from "@/lib/fetch";

export const authApi = {
  register: async (email: string, password: string) => {
    const res = await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || "Registration failed");
    }

    return res.json();
  },
};
