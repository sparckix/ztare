const apiTarget = process.env.ZTARE_WORKBENCH_API_TARGET || "http://127.0.0.1:8765";

export default {
  server: {
    host: "127.0.0.1",
    port: 5174,
    proxy: {
      "/api": apiTarget
    }
  },
  preview: {
    host: "127.0.0.1",
    port: 4174
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
};
