import type { Metadata } from "next";
import { AdminPage } from "@/components/pages/admin/AdminPage";

export const metadata: Metadata = {
  title: "Admin — InterviewLeap",
  robots: { index: false },
};

export default function Admin() {
  return <AdminPage />;
}
