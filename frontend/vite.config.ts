import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Tauri: don't clear the terminal, and expose TAURI_* env vars to the client.
  clearScreen: false,
  envPrefix: ["VITE_", "TAURI_"],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": "http://localhost:8000",
      "/v1": "http://localhost:8000",
      "/demo": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/ready": "http://localhost:8000",
    },
  },
  build: { outDir: "dist" },
});
