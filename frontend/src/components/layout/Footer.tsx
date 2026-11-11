import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-border/30 py-10 px-6">
      <div className="container mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <span className="font-display font-bold gradient-text">
          InterviewLeap
        </span>
        <div className="flex items-center gap-6">
          <Link
            href="/privacy"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Privacy Policy
          </Link>
          <Link
            href="/terms"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Terms of Service
          </Link>
        </div>
        <p className="text-sm text-muted-foreground">
          © 2026 InterviewLeap. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
