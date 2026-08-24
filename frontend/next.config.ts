import type { NextConfig } from "next";

// Static export is opt in and only for the Tauri desktop bundle. A normal web or
// CI build keeps the server runtime so the app router API routes (auth, git) work.
// The Tauri build sets NEXT_OUTPUT_EXPORT=1 in its beforeBuildCommand.
const staticExport = process.env.NEXT_OUTPUT_EXPORT === "1";

const nextConfig: NextConfig = {
  ...(staticExport ? { output: "export" } : {}),

  // Silence turbopack "multiple lockfiles" warning
  turbopack: {
    root: __dirname,
  },

  // For Tauri: Disable Node.js image optimization
  images: {
    unoptimized: true,
  },
};

export default nextConfig;