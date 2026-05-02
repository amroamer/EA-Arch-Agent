import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
// Mounted under /EAArchAgent/ so it can co-exist with other KPMG apps
// behind a shared nginx (matches Slide-Generator's /slide-generator/ and
// Data-Steward-Assistant's /dataowner/ pattern).
export default defineConfig({
  plugins: [react()],
  base: "/EAArchAgent/",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: {
      // In dev, /EAArchAgent/api/* is proxied to the backend with the
      // /EAArchAgent prefix STRIPPED — the backend mounts routes at
      // /api/* and is unaware of the public path prefix (mirrors the
      // production nginx rewrite `^/EAArchAgent/api/(.*) /api/$1 break;`).
      // VITE_API_PROXY_TARGET lets Docker Compose override the host:
      // inside the container the backend is reachable as http://backend:8000,
      // locally it's localhost:8000.
      "/EAArchAgent/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/EAArchAgent/, ""),
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    allowedHosts: ["digital-foundation.uksouth.cloudapp.azure.com"],
  },
});