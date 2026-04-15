import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./playwright",
  timeout: 30000,
  retries: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "results/playwright_results.json" }],
    ["html", { outputFolder: "results/playwright_report", open: "never" }],
  ],
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:8080",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
});