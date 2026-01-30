import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vitest/config";
import { visualizer } from "rollup-plugin-visualizer";

export default defineConfig({
  plugins: [
    sveltekit(),
    visualizer({
      filename: "stats.html",
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Skip for SSR build (only apply to client)
          if (id.includes("node_modules")) {
            // Carbon charts - heavy dependency
            if (id.includes("@carbon/charts") || id.includes("d3")) {
              return "charts";
            }
            // Carbon components
            if (
              id.includes("carbon-components-svelte") ||
              id.includes("carbon-icons-svelte")
            ) {
              return "carbon";
            }
            // EditorJS
            if (id.includes("@editorjs")) {
              return "editor";
            }
            // Other vendor libraries
            if (id.includes("date-fns") || id.includes("svelte-dnd-action")) {
              return "vendor";
            }
          }
        },
      },
    },
  },
  test: {
    include: ["src/**/*.{test,spec}.{js,ts}"],
    environment: "jsdom",
    globals: true,
  },
});
