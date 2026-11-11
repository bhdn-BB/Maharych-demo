import Link from "next/link";
import { Brain } from "lucide-react";

interface LogoProps {
  variant?: "full" | "text";
  href?: string;
  className?: string;
}

function LogoContent({ variant = "full", className }: LogoProps) {
  return (
    <div className={`flex items-center gap-3 ${className ?? ""}`}>
      {variant === "full" && (
        <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center glow-border">
          <Brain className="w-6 h-6 text-primary" />
        </div>
      )}
      <span className="text-2xl font-bold gradient-text font-display">
        InterviewLeap
      </span>
    </div>
  );
}

export function Logo({ variant = "full", href, className }: LogoProps) {
  if (href) {
    return (
      <Link href={href} className={`flex items-center justify-center ${className ?? ""}`}>
        <LogoContent variant={variant} />
      </Link>
    );
  }

  return <LogoContent variant={variant} className={className} />;
}
