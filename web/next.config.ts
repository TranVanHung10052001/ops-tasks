import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_API_SECRET: process.env.NEXT_PUBLIC_API_SECRET || "ops-tasks-secret-change-me",
  },
};

export default nextConfig;
