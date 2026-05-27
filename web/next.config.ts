import path from "node:path";
import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const isProduction = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  reactCompiler: isProduction,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "play.pokemonshowdown.com",
        pathname: "/sprites/**",
      },
    ],
  },
  turbopack: {
    root: currentDirectory,
  },
};

export default nextConfig;
