import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

// vite-plugin-singlefile inlines JS + CSS into the HTML so the
// final dist/index.html opens directly via file:// without a server.
// ES module loading and fetch() don't work over file:// because of
// browser CORS, so the singlefile build is the only path that gives
// the operator a "double-click index.html and it works" experience.
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  base: "./",
  server: { port: 5183 },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // Singlefile plugin needs these to actually inline everything
    cssCodeSplit: false,
    assetsInlineLimit: 100_000_000,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
});
