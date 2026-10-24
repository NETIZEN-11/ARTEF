/** @type {import('next').NextConfig} */
const apiProxyTarget = (process.env.API_PROXY_TARGET || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/+$/, "");
const normalizedApiProxyTarget = apiProxyTarget.endsWith("/api/v1") ? apiProxyTarget : `${apiProxyTarget}/api/v1`;

const nextConfig = {
  reactStrictMode: false, // Disable strict mode to reduce web vitals
  // The Docker image copies `.next/standalone`, so the standalone output is
  // required there. It is opt-in because the standalone bundler recreates
  // the pnpm symlink farm, which requires elevated privileges on Windows and
  // fails the local build with EPERM. The Dockerfile sets the flag.
  ...(process.env.NEXT_OUTPUT_STANDALONE === "true" ? { output: "standalone" } : {}),
  eslint: {
    // Lint runs as its own CI step (`pnpm lint`) instead of inside `next build`.
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  images: {
    remotePatterns: [{ protocol: "http", hostname: "localhost" }],
  },
  // Production optimizations
  productionBrowserSourceMaps: false,
  onDemandEntries: {
    maxInactiveAge: 25 * 1000,
    pagesBufferLength: 2,
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${normalizedApiProxyTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
