import type { NextConfig } from "next";

import { validatePublicConfig } from "./lib/config";

validatePublicConfig();

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
};

export default nextConfig;
