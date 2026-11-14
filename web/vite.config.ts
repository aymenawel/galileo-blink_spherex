import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/** The Python server that owns the engine; the dev server forwards data requests to it. */
const ENGINE = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": ENGINE,
      "/files": ENGINE,
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
