import { Metadata } from "next";
import { AuthForm } from "@/components/pages/auth/AuthForm";

export const metadata: Metadata = {
  title: "Sign In - InterviewLeap",
};

export default function LoginPage() {
  return <AuthForm mode="login" />;
}
