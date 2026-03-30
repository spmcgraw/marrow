import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/auth/callback", "/_next", "/favicon.ico"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // If OIDC is not enabled, skip auth checks
  if (process.env.NEXT_PUBLIC_OIDC_ENABLED !== "true") {
    return NextResponse.next();
  }

  // Check for session cookie (set by the backend with Domain=localhost or shared domain)
  const session = request.cookies.get("freehold_session");
  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Cookie exists — let the request proceed.
  // The backend validates the JWT on each API call.
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
