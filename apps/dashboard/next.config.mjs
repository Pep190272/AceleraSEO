/** @type {import('next').NextConfig} */
const nextConfig = {
  // The engine base URL is read server-side only (see src/lib/engine.ts).
  reactStrictMode: true,
  // Emit a self-contained server bundle for a tiny production Docker image.
  output: "standalone",
};

export default nextConfig;
