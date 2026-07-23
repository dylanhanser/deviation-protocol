import { defineConfig } from "vitest/config";

export default defineConfig({
  envDir: false,
  test: {
    environment: "node",
    include: [
      "tools/validate-public-scenario-catalog.validation.ts",
    ],
    fileParallelism: false,
    maxWorkers: 1,
    testTimeout: 5_000,
  },
});
