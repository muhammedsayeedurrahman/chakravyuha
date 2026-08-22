import type { NextConfig } from "next";
import path from "path";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Build-time sanity check — visible in Vercel build logs
console.log(`[next.config] BACKEND_URL = ${BACKEND_URL}`);

const nextConfig: NextConfig = {
  reactCompiler: true,
  // Pin turbopack root to this package to avoid confusion from stray
  // package-lock.json files in parent directories of the monorepo.
  turbopack: {
    root: path.resolve(__dirname),
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${BACKEND_URL}/health`,
      },
    ];
  },
};

export default nextConfig;
