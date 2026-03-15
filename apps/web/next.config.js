/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        // Proxy API calls to the FastAPI backend during development
        // so the frontend can call /api/jobs instead of http://localhost:8000/jobs
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
