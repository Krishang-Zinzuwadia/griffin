/**
 * DELETE /api/auth/vercel/disconnect
 *
 * Removes the stored Vercel token from .env.local.
 */
import { NextResponse } from "next/server";
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

function removeEnvVar(content: string, key: string): string {
  return content
    .split("\n")
    .filter((l) => !l.trim().startsWith(`${key}=`))
    .join("\n");
}

export async function DELETE() {
  try {
    let content = await readEnvFile();
    content = removeEnvVar(content, "VERCEL_TOKEN");
    await writeFile(ENV_PATH, content, "utf-8");

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
