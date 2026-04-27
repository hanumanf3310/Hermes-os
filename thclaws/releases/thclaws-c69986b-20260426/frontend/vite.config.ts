import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile()],
  // banner.txt lives at the thclaws repo root so the Rust REPL and the
  // GUI terminal share one source of truth. Vite's default fs.allow
  // scope is the frontend dir; widen it by one so `?raw` imports resolve.
  server: {
    fs: {
      allow: [".."],
    },
  },
});
