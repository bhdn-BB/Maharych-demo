import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Service — InterviewLeap",
  description: "Terms and conditions for using the InterviewLeap platform.",
};

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen gradient-bg">
      <div className="container mx-auto max-w-3xl px-6 py-24">
        <h1 className="text-4xl font-display font-bold mb-2">
          Terms of Service
        </h1>
        <p className="text-muted-foreground mb-12">
          Last updated: March 20, 2026
        </p>

        <div className="space-y-10 text-foreground/90 leading-relaxed">
          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              1. Acceptance of Terms
            </h2>
            <p>
              By accessing or using Interview Leap (&quot;the Service&quot;),
              you agree to be bound by these Terms of Service. If you do not
              agree to these terms, do not use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              2. Description of Service
            </h2>
            <p>
              Interview Leap is an AI-powered mock interview platform. You can
              select your experience level, target position, and focus area, and
              then participate in a real-time voice-based interview with an AI
              interviewer. The Service is designed for practice and educational
              purposes only.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              3. Account Registration
            </h2>
            <p>
              To use the Service, you must create an account using an email
              address and password or by signing in with Google. You are
              responsible for maintaining the confidentiality of your account
              credentials. You agree to provide accurate and current information
              during registration.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              4. Acceptable Use
            </h2>
            <p>You agree not to:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>
                Use the Service for any unlawful purpose or in violation of any
                applicable laws
              </li>
              <li>
                Attempt to gain unauthorized access to the Service, other
                accounts, or our systems
              </li>
              <li>
                Interfere with or disrupt the integrity or performance of the
                Service
              </li>
              <li>
                Transmit harmful, offensive, or inappropriate content through
                the audio interface
              </li>
              <li>
                Use automated scripts, bots, or scrapers to access the Service
              </li>
              <li>
                Reverse-engineer, decompile, or disassemble any part of the
                Service
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              5. Intellectual Property
            </h2>
            <p>
              All content, features, and functionality of the Service —
              including but not limited to text, graphics, logos, AI models, and
              software — are owned by Interview Leap and protected by
              intellectual property laws. You may not reproduce, distribute, or
              create derivative works from any part of the Service without our
              prior written consent.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              6. User Content
            </h2>
            <p>
              By using the Service, you grant Interview Leap a non-exclusive,
              worldwide, royalty-free license to process, store, and analyze the
              audio and text content you submit during interviews for the
              purpose of providing and improving the Service. You retain
              ownership of your original content.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              7. AI-Generated Content
            </h2>
            <p>
              The interview questions, feedback, and responses provided by our
              AI are generated automatically and are for practice purposes only.
              Interview Leap does not guarantee the accuracy, completeness, or
              suitability of AI-generated content. You should not rely on it as
              professional career advice.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              8. Privacy
            </h2>
            <p>
              Your use of the Service is also governed by our{" "}
              <Link href="/privacy" className="text-primary hover:underline">
                Privacy Policy
              </Link>
              , which describes how we collect, use, and protect your data.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              9. Disclaimers
            </h2>
            <p>
              The Service is provided &quot;as is&quot; and &quot;as
              available&quot; without warranties of any kind, whether express or
              implied, including but not limited to implied warranties of
              merchantability, fitness for a particular purpose, and
              non-infringement. We do not warrant that the Service will be
              uninterrupted, error-free, or secure.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              10. Limitation of Liability
            </h2>
            <p>
              To the fullest extent permitted by law, Interview Leap shall not
              be liable for any indirect, incidental, special, consequential, or
              punitive damages arising from your use of or inability to use the
              Service, even if we have been advised of the possibility of such
              damages.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              11. Account Termination
            </h2>
            <p>
              We reserve the right to suspend or terminate your account at our
              discretion if you violate these Terms or engage in conduct that we
              determine to be harmful to the Service or other users. You may
              delete your account at any time by contacting us.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              12. Changes to These Terms
            </h2>
            <p>
              We may revise these Terms at any time by posting the updated
              version on this page. Your continued use of the Service after
              changes are posted constitutes your acceptance of the revised
              Terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-display font-semibold mb-3">
              13. Contact
            </h2>
            <p>
              If you have questions about these Terms, please contact us at{" "}
              <a
                href="mailto:legal@interviewleap.com"
                className="text-primary hover:underline"
              >
                legal@interviewleap.com
              </a>
              .
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
