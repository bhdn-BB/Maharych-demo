import { useSession } from "next-auth/react";

export function useBackendToken() {
  const { data: session } = useSession();
  return session?.backendToken ?? "";
}
