import { describe, expect, it } from "vitest";

import { createViteConfig } from "./vite.config";

describe("Vite mode isolation", () => {
  it("disables all dotenv loading only for deterministic-demo mode", () => {
    expect(createViteConfig("deterministic-demo").envDir).toBe(false);
  });

  it.each(["development", "production", "test", "ordinary-unknown"])(
    "retains Vite default dotenv behavior for %s mode",
    (mode) => {
      expect(createViteConfig(mode).envDir).toBeUndefined();
    },
  );

  it("preserves the API proxy and Web test configuration", () => {
    const config = createViteConfig("deterministic-demo");
    const proxy = config.server?.proxy?.["/api"];
    if (typeof proxy !== "object" || proxy === null) {
      throw new Error("expected an object API proxy configuration");
    }
    if (proxy.rewrite === undefined) {
      throw new Error("expected the API proxy rewrite");
    }

    expect(proxy.target).toBe("http://127.0.0.1:8000");
    expect(proxy.changeOrigin).toBe(true);
    expect(proxy.rewrite("/api/v1/scenarios")).toBe("/v1/scenarios");
    expect(config.test).toEqual({
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      css: true,
    });
  });
});
