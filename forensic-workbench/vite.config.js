import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const dashboardModules = path.resolve(here, "../analytics/public/dashboard/node_modules");

export default {
  resolve: {
    alias: {
      react: path.join(dashboardModules, "react/index.js"),
      "react-dom/client": path.join(dashboardModules, "react-dom/client.js")
    }
  },
  server: {
    host: "127.0.0.1",
    port: 5174,
    proxy: {
      "/api": "http://127.0.0.1:8765"
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
