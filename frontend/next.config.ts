import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  // Only use static export for Tauri production builds
  ...(isProd ? { output: "export" } : {}),

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