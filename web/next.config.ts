import path from "node:path";
import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.join(currentDirectory, "..");

const nextConfig: NextConfig = {
  reactCompiler: true,
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
    root: repositoryRoot,
  },
  outputFileTracingRoot: repositoryRoot,
  outputFileTracingIncludes: {
    "/": ["../examples/**/*"],
  },
};

export default nextConfig;
