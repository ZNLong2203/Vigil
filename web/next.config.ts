import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export. There is no SSR need here — no SEO surface, the personas are
  // fixed, and every byte of data comes from the Python API at runtime. Shipping
  // a static bundle means one Cloud Run service instead of two.
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
