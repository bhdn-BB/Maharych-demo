import { Metadata } from "next";
import { AuthForm } from "@/components/pages/auth/AuthForm";

export const metadata: Metadata = {
  title: "Create Account - InterviewLeap",
};

export default function RegisterPage() {
  return <AuthForm mode="register" />;
}
