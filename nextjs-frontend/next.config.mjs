/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy to FastAPI backend is handled by the App Router catch-all route at
  // src/app/api/backend/[...path]/route.ts, which sets a 120-second timeout.
  // The old rewrite has been removed because rewrites have no timeout control.
};

export default nextConfig;
