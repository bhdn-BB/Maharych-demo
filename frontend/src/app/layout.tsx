import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "InterviewLeap",
  description:
    "AI-Powered Mock Interviews — Practice with an AI interviewer tailored to your experience level and desired position.",
  openGraph: {
    title: "InterviewLeap",
    description: "AI-Powered Mock Interviews",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
