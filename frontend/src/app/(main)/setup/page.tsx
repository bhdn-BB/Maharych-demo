import { interviewOptionsApi } from "@/api/interview-options/interview-options.api";
import { SetupForm } from "@/components/pages/setup/SetupForm";

export const dynamic = "force-dynamic";

export default async function SetupPage() {
  const options = await interviewOptionsApi.getAll();

  return <SetupForm options={options} />;
}
