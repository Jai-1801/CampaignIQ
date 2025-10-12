// vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    // ===================================
    // ✨ ADDED PROXY CONFIGURATION HERE ✨
    // ===================================
    proxy: {
      // Proxy requests starting with /api
      '/api': {
        // Target the Flask server running on port 5000
        target: 'http://127.0.0.1:5000',
        // Necessary for virtual hosted sites
        changeOrigin: true,
        // Optional: Rewrite the path if your Flask app didn't use /api, 
        // but since yours does, we keep it as is.
      },
    },
    // ===================================
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));