/**
 * GET /api/auth/vercel
 *
 * Redirects the user to Vercel's OAuth authorization page.
 * Requires VERCEL_CLIENT_ID to be set in .env.local.
 */
import { NextResponse } from "next/server";

export async function GET() {
  const clientId = process.env.VERCEL_CLIENT_ID;

  if (!clientId) {
    return NextResponse.json(
      {
        error:
          "VERCEL_CLIENT_ID is not configured. Add it to .env.local to enable Vercel sign-in.",
      },
      { status: 500 },
    );
  }

  // Build the Vercel OAuth URL
  // Docs: https://vercel.com/docs/rest-api/reference#creating-an-oauth2-token
  const redirectUri = `${process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"}/api/auth/vercel/callback`;

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    // No specific scope needed — default scope provides deploy access
  });

  const vercelAuthUrl = `https://vercel.com/integrations/new?${params.toString()}`;

  return NextResponse.redirect(vercelAuthUrl);
}
