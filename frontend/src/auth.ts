import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";
import { apiFetch } from "./lib/fetch";

// Go verifies the signature on every API request. Here we expire the web session's
// API capability with the issued token, rather than keeping it for NextAuth's longer lifetime.
function apiTokenIsCurrent(value: unknown): value is string {
  if (typeof value !== "string") return false;
  try {
    const payload = value.split(".")[1];
    if (!payload) return false;
    const claims = JSON.parse(
      atob(payload.replace(/-/g, "+").replace(/_/g, "/")),
    );
    return (
      typeof claims.exp === "number" &&
      Number.isFinite(claims.exp) &&
      claims.exp * 1000 > Date.now()
    );
  } catch {
    return false;
  }
}

// UI-only hint: the Go API enforces admin access from the signed token itself.
function roleFromToken(value: unknown): "admin" | "user" {
  if (typeof value !== "string") return "user";
  try {
    const payload = value.split(".")[1];
    if (!payload) return "user";
    const claims = JSON.parse(
      atob(payload.replace(/-/g, "+").replace(/_/g, "/")),
    );
    return claims.role === "admin" ? "admin" : "user";
  } catch {
    return "user";
  }
}

declare module "next-auth" {
  interface Session {
    backendToken?: string;
    user: {
      id?: string;
      email?: string | null;
      role?: "admin" | "user";
    };
  }

  interface User {
    backendToken?: string;
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  trustHost: true,
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
    Credentials({
      credentials: {
        email: {},
        password: {},
      },
      async authorize(credentials) {
        const res = await apiFetch("/auth/login", {
          method: "POST",
          body: JSON.stringify({
            email: credentials.email,
            password: credentials.password,
          }),
        });

        if (!res.ok) return null;

        const data = await res.json();
        return {
          id: String(data.user.id),
          email: data.user.email,
          backendToken: data.token,
        };
      },
    }),
  ],
  session: { strategy: "jwt" },
  pages: {
    signIn: "/login",
  },
  callbacks: {
    authorized({ auth, request }) {
      const isAuthed = !!auth?.user && !!auth?.backendToken;
      const isProtected = [
        "/dashboard",
        "/setup",
        "/interview",
        "/profile",
      ].some((p) => request.nextUrl.pathname.startsWith(p));
      if (isProtected && !isAuthed) return false;
      if (request.nextUrl.pathname.startsWith("/admin")) {
        if (!isAuthed) return false;
        if (auth?.user?.role !== "admin") {
          return Response.redirect(new URL("/dashboard", request.nextUrl));
        }
      }
      return true;
    },
    async jwt({ token, user, account }) {
      if (user) {
        token.backendToken = (user as { backendToken?: string }).backendToken;
        token.userId = user.id;
      }

      if (account?.provider === "google") {
        if (!account.id_token)
          throw new Error("Google did not return an ID token");
        try {
          const res = await apiFetch("/auth/google", {
            method: "POST",
            body: JSON.stringify({ id_token: account.id_token }),
          });

          if (res.ok) {
            const data = await res.json();
            token.backendToken = data.token;
            token.userId = String(data.user.id);
          } else {
            throw new Error("Backend Google sign-in rejected");
          }
        } catch (err) {
          throw new Error("Google sign-in could not create an API session", {
            cause: err,
          });
        }
      }

      if (!apiTokenIsCurrent(token.backendToken)) {
        delete token.backendToken;
        delete token.userId;
        if (user || account)
          throw new Error("Sign-in did not produce a current API token");
      }
      return token;
    },
    session({ session, token }) {
      session.backendToken = token.backendToken as string | undefined;
      if (session.user) {
        session.user.id = token.userId as string | undefined;
        session.user.role = roleFromToken(token.backendToken);
      }
      return session;
    },
  },
});
