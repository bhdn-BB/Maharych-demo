import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { profileApi } from "@/api/profile/profile.api";

/** Shares the ["profile", userId] cache entry with the profile form. */
export function useProfile() {
  const { data: session } = useSession();
  const token = session?.backendToken ?? "";
  const userId = session?.user?.id;
  return useQuery({
    queryKey: ["profile", userId],
    queryFn: () => profileApi.get(token),
    enabled: !!token && !!userId,
  });
}
