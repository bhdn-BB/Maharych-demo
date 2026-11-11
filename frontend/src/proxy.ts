export { auth as proxy } from "@/auth";

export const config = {
  matcher: ["/dashboard/:path*", "/setup/:path*", "/interview/:path*", "/profile/:path*", "/admin/:path*"],
};
