import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy — InterviewLeap",
  description: "How InterviewLeap collects, uses, and protects your data.",
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen gradient-bg">
      <div className="container mx-auto max-w-3xl px-6 py-24">
        <h1 className="text-4xl font-display font-bold mb-2">
          Privacy Policy
        </h1>
        <p className="text-muted-foreground mb-12">
          Last updated: March 20, 2026
        </p>

        <div className="space-y-10 text-foreground/90 leading-relaxed">
          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              1. Introduction
            </h2>
            <p>
              Interview Leap (&quot;we&quot;, &quot;our&quot;, &quot;us&quot;)
              operates an AI-powered mock interview platform. This Privacy Policy
              explains how we collect, use, disclose, and safeguard your
              information when you use our website and services.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              2. Information We Collect
            </h2>
            <h3 className="font-semibold mt-4 mb-2">
              Account Information
            </h3>
            <p>
              When you create an account, we collect your email address. If you
              sign in with Google, we receive your email address and Google
              account identifier from Google&apos;s OAuth service. We do not
              access your Google contacts, calendar, or any other Google data.
            </p>
            <h3 className="font-semibold mt-4 mb-2">
              Interview Data
            </h3>
            <p>
              During mock interviews, we collect the audio you record through
              your microphone, your selected interview preferences (experience
              level, position, focus area), and the text transcripts and AI
              responses generated during the session.
            </p>
            <h3 className="font-semibold mt-4 mb-2">
              Technical Data
            </h3>
            <p>
              We automatically collect standard server logs including IP
              address, browser type, and access timestamps for security and
              operational purposes.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              3. How We Use Your Information
            </h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                Authenticate your identity and maintain your account
              </li>
              <li>
                Conduct AI-powered mock interviews and deliver real-time
                audio/text responses
              </li>
              <li>
                Store your interview history so you can review past sessions
              </li>
              <li>
                Improve our AI models and service quality
              </li>
              <li>
                Ensure security, prevent fraud, and enforce our terms
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              4. Authentication &amp; Third-Party Services
            </h2>
            <p>
              We offer sign-in via Google OAuth. When you choose this option,
              Google shares your email address and basic profile identifier with
              us. Your Google password is never shared with Interview Leap. We
              use JSON Web Tokens (JWT) to manage sessions — no session data is
              stored in cookies on our servers.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              5. Data Storage &amp; Security
            </h2>
            <p>
              Your data is stored in a PostgreSQL database. Passwords for
              credential-based accounts are hashed with bcrypt and never stored
              in plain text. Audio data is streamed in real time to our AI
              service and is not permanently stored after the session ends unless
              explicitly stated otherwise. We use HTTPS for all client-server
              communication and authenticate WebSocket connections with JWT
              tokens.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              6. Data Sharing
            </h2>
            <p>
              We do not sell your personal data. We may share information only
              in the following cases:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>
                With AI service providers that process your audio during
                interviews, strictly for providing the service
              </li>
              <li>
                When required by law, regulation, or legal process
              </li>
              <li>
                To protect the rights, safety, or property of Interview Leap or
                its users
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              7. Your Rights
            </h2>
            <p>You have the right to:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Access the personal data we hold about you</li>
              <li>Request correction of inaccurate data</li>
              <li>Request deletion of your account and associated data</li>
              <li>Withdraw consent for data processing at any time</li>
            </ul>
            <p className="mt-2">
              To exercise any of these rights, contact us at the email address
              listed below.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              8. Cookies
            </h2>
            <p>
              We use essential cookies only for authentication session
              management. We do not use advertising or analytics cookies.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              9. Changes to This Policy
            </h2>
            <p>
              We may update this Privacy Policy from time to time. We will
              notify you of material changes by posting the updated policy on
              this page with a revised &quot;Last updated&quot; date.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              10. Contact
            </h2>
            <p>
              If you have questions about this Privacy Policy, please contact us
              at{" "}
              <a
                href="mailto:privacy@interviewleap.com"
                className="text-primary hover:underline"
              >
                privacy@interviewleap.com
              </a>
              .
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
