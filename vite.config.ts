import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 用户站点 shimolinchi.github.io 部署在根路径，base 用 "/"
export default defineConfig({
  plugins: [react()],
  base: "/",
});
