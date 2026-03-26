import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  // Ensure neo4j-driver is included in standalone output
  serverExternalPackages: ['neo4j-driver'],
};

export default nextConfig;
