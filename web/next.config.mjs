/** @type {import('next').NextConfig} */
const isStaticExport = process.env.NEXT_STATIC_EXPORT === "1";

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  ...(isStaticExport
    ? {
        output: "export",
        trailingSlash: true,
        images: { unoptimized: true },
      }
    : {}),
  ...(!isStaticExport
    ? {
        experimental: {
          optimizePackageImports: ["lucide-react"],
          serverActions: {
            bodySizeLimit: "10mb",
          },
        },
      }
    : {
        experimental: {
          optimizePackageImports: ["lucide-react"],
        },
      }),
  // Allow MinIO presigned URLs and thumbnail images (dev / non-export)
  ...(!isStaticExport
    ? {
        images: {
          remotePatterns: [
            { protocol: "http", hostname: "localhost", port: "9000" },
            { protocol: "https", hostname: "**.amazonaws.com" },
            { protocol: "https", hostname: "**.r2.cloudflarestorage.com" },
          ],
        },
      }
    : {}),
  // Proxy /api/* to FastAPI in dev — not used in static export (sidecar serves API)
  ...(!isStaticExport
    ? {
        async rewrites() {
          const apiUrl = process.env.API_INTERNAL_URL || "http://localhost:8000";
          return [
            {
              source: "/api/:path*",
              destination: `${apiUrl}/api/:path*`,
            },
            {
              source: "/storage/:path*",
              destination: `${apiUrl}/storage/:path*`,
            },
          ];
        },
        async headers() {
          return [
            {
              source: "/api/jobs/:job_id/progress",
              headers: [
                { key: "Cache-Control", value: "no-cache, no-transform" },
                { key: "X-Accel-Buffering", value: "no" },
              ],
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
