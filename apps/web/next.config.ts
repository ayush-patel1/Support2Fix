import type { NextConfig } from "next";

// Same-origin API access: the browser only ever talks to `web`, which
// forwards /api/* to the FastAPI service. This is why there's no CORS
// configuration anywhere in the stack — see ADR-001 D10 and
// docs/architecture/system-design.md §5, §7.
const apiOrigin = process.env.API_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
