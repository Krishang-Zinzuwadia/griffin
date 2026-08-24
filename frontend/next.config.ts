import type { NextConfig } from "next";

// Static export is opt in and only for the Tauri desktop bundle. A normal web or
// CI build keeps the server runtime so the app router API routes (auth, git) work.
// The Tauri build sets NEXT_OUTPUT_EXPORT=1 in its beforeBuildCommand.
const staticExport = process.env.NEXT_OUTPUT_EXPORT === "1";

// A static export cannot include app router route handlers that rely on Node
// APIs. The auth and git handlers under src/app/api use fs and child_process, so
// an export build fails while collecting page data for them. Every page and
// layout in this app uses a .tsx extension and the only .ts route files are those
// API handlers, so for the export build we drop the .ts and .js page extensions.
// That leaves the /api segment out of the export, while the normal build keeps
// the default extensions and serves the four handlers as dynamic server routes.
const pageExtensions = staticExport
  ? ["tsx", "jsx"]
  : ["tsx", "ts", "jsx", "js"];

const nextConfig: NextConfig = {
  ...(staticExport ? { output: "export" } : {}),

  pageExtensions,

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
