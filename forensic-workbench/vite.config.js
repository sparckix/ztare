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
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("reactflow") || id.includes("d3-")) return "research-map";
          if (id.includes("katex") || id.includes("marked") || id.includes("dompurify")) return "documents";
          if (id.includes("lucide-react") || id.includes("@tabler/icons-react")) return "icons";
          if (id.includes("react") || id.includes("scheduler")) return "react";
          return "vendor";
        }
      }
    }
  }
};
