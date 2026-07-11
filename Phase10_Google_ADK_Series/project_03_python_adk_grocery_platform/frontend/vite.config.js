import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The A2UI server (app/a2ui_server.py) runs on :8000. We proxy /api to it so the
// browser talks same-origin and the FastAPI CORS list stays short.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5174,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
