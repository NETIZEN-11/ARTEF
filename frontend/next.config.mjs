/** @type {import('next').NextConfig} */
const apiProxyTarget = (process.env.API_PROXY_TARGET || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/+$/, "");
const normalizedApiProxyTarget = apiProxyTarget.endsWith("/api/v1") ? apiProxyTarget : `${apiProxyTarget}/api/v1`;

const nextConfig = {
  reactStrictMode: false, // Disable strict mode to reduce web vitals
  eslint: {
    // Skip ESLint during production builds to avoid hanging
    // Run `npm run lint` separately for linting
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Type checking is already verified separately
    ignoreBuildErrors: false,
  },
  experimental: {
    optimizePackageImports: ["lucide-react", "@radix-ui/react-icons"],
  },
  images: {
    remotePatterns: [{ protocol: "http", hostname: "localhost" }],
  },
  // Production optimizations
  productionBrowserSourceMaps: false,
  // Suppress non-critical errors in development
  onDemandEntries: {
    maxInactiveAge: 25 * 1000,
    pagesBufferLength: 2,
  },
  // Webpack config to exclude web-vitals
  webpack: (config, { dev, isServer }) => {
    if (!isServer) {
      // Completely remove web-vitals from bundle
      config.resolve.alias = {
        ...config.resolve.alias,
        'next/dist/compiled/web-vitals': false,
        'web-vitals': false,
      };
      
      // DefinePlugin skipped (web-vitals aliased to false above is sufficient)
    }
    return config;
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
