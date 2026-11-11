import type { Metadata } from "next";
import { ProfileForm } from "@/components/pages/profile/ProfileForm";

export const metadata: Metadata = {
  title: "Profile — InterviewLeap",
  description: "Manage your InterviewLeap account and preferences.",
};

export default function ProfilePage() {
  return (
    <div className="min-h-screen gradient-bg">
      <div className="container mx-auto max-w-3xl px-6 py-24">
        <h1 className="text-4xl font-display font-bold mb-4">Profile</h1>
        <ProfileForm />
      </div>
    </div>
  );
}
