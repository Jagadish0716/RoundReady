import type { NextConfig } from "next";

import { validatePublicConfig } from "./lib/config";

validatePublicConfig();

const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
