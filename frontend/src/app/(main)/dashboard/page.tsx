import type { Metadata } from "next";
import { interviewOptionsApi } from "@/api/interview-options/interview-options.api";
import { DashboardPage } from "@/components/pages/dashboard/DashboardPage";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Dashboard — InterviewLeap",
  description: "Browse and configure your mock interview session.",
};

export default async function Dashboard() {
  const options = await interviewOptionsApi.getAll();
  return <DashboardPage options={options} />;
}
