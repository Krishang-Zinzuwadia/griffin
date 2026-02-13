/**
 * GET /api/auth/vercel/callback
 *
 * Handles the Vercel OAuth callback.
 * Exchanges the authorization code for an access token, persists
 * the token to .env.local, and redirects back to the app.
 */
import { NextRequest, NextResponse } from "next/server";
import { readFile, writeFile } from "fs/promises";
import { join } from "path";

const ENV_PATH = join(process.cwd(), ".env.local");

async function readEnvFile(): Promise<string> {
  try {
    return await readFile(ENV_PATH, "utf-8");
  } catch {
    return "";
  }
}

function upsertEnvVar(content: string, key: string, value: string): string {
  const lines = content.split("\n");
  const idx = lines.findIndex((l) => l.trim().startsWith(`${key}=`));
  const entry = `${key}=${value}`;

  if (idx !== -1) {
    lines[idx] = entry;
  } else {
    if (lines.length > 0 && lines[lines.length - 1].trim() !== "") {
      lines.push("");
    }
    lines.push(entry);
  }

  return lines.join("\n");
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

  if (!code) {
    return NextResponse.redirect(
      `${appUrl}?auth_error=${encodeURIComponent("No authorization code received from Vercel.")}`,
    );
  }

  const clientId = process.env.VERCEL_CLIENT_ID;
  const clientSecret = process.env.VERCEL_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    return NextResponse.redirect(
      `${appUrl}?auth_error=${encodeURIComponent("Vercel OAuth credentials not configured.")}`,
    );
  }

  try {
    const redirectUri = `${appUrl}/api/auth/vercel/callback`;

    // Exchange code for access token
    const tokenRes = await fetch("https://api.vercel.com/v2/oauth/access_token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret,
        code,
        redirect_uri: redirectUri,
      }),
    });

    if (!tokenRes.ok) {
      const errText = await tokenRes.text();
      return NextResponse.redirect(
        `${appUrl}?auth_error=${encodeURIComponent(`Vercel token exchange failed: ${errText}`)}`,
      );
    }

    const tokenData = await tokenRes.json();
    const accessToken: string = tokenData.access_token;

    // Persist token to .env.local
    let content = await readEnvFile();
    content = upsertEnvVar(content, "VERCEL_TOKEN", accessToken);
    await writeFile(ENV_PATH, content, "utf-8");

    // Redirect back to app with success flag
    return NextResponse.redirect(`${appUrl}?vercel_auth=success`);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.redirect(
      `${appUrl}?auth_error=${encodeURIComponent(message)}`,
    );
  }
}
