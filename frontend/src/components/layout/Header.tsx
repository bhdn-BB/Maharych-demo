"use client";

import Link from "next/link";
import { signOut, useSession } from "next-auth/react";
import { LogOut, User, ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Header() {
  const { data: session } = useSession();
  const isAuthed = !!session?.user;

  return (
    <nav className="fixed top-0 w-full z-50 glass-strong">
      <div className="container mx-auto flex items-center justify-between py-4 px-6">
        <Link href="/" className="text-xl font-display font-bold gradient-text">
          InterviewLeap
        </Link>
        <div className="flex items-center gap-3">
          {isAuthed ? (
            <>
                {session?.user?.role === "admin" && (
                  <Button asChild size="sm" variant="ghost">
                    <Link href="/admin">Admin</Link>
                  </Button>
                )}
                <Button asChild
                  size="sm"
                  className="bg-primary/20 text-primary hover:bg-primary/30 border border-primary/30"
                >
                  <Link href="/dashboard"><ClipboardList aria-hidden="true" className="h-4 w-4" />My interviews</Link>
                </Button>
                <Button asChild
                  size="icon"
                  variant="ghost"
                  className="rounded-full border border-primary/30 text-primary hover:bg-primary/20"
                >
                  <Link href="/profile" aria-label="Profile"><User aria-hidden="true" className="h-4 w-4" /></Link>
                </Button>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  aria-label="Sign out"
                  title="Sign out"
                  onClick={() => void signOut({ callbackUrl: "/" })}
                  className="rounded-full text-muted-foreground hover:text-foreground hover:bg-primary/10"
                >
                  <LogOut aria-hidden="true" className="h-4 w-4" />
                </Button>
            </>
          ) : (
              <Button asChild
                size="sm"
                className="bg-primary/20 text-primary hover:bg-primary/30 border border-primary/30"
              >
                <Link href="/login">Sign In</Link>
              </Button>
          )}
        </div>
      </div>
    </nav>
  );
}
