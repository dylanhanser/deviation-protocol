import { readFile } from "node:fs/promises";
import path from "node:path";

import { expect, test } from "vitest";

import { publicScenarioCatalogSchema } from "../src/api/schemas";

test("the captured public scenario catalog matches the production Web schema", async () => {
  const responseFile =
    process.env.DEVIATION_DEMO_SCENARIO_RESPONSE_FILE;
  if (responseFile === undefined || responseFile.trim() === "") {
    throw new Error("scenario response file path is required");
  }
  if (!path.isAbsolute(responseFile)) {
    throw new Error("scenario response file path must be absolute");
  }

  const responseBytes = await readFile(responseFile);
  let responseText: string;
  try {
    responseText = new TextDecoder("utf-8", { fatal: true }).decode(
      responseBytes,
    );
  } catch {
    throw new Error("scenario response file is not valid UTF-8");
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(responseText);
  } catch {
    throw new Error("scenario response file is not valid JSON");
  }

  const result = publicScenarioCatalogSchema.safeParse(parsed);
  expect(
    result.success,
    "scenario response does not match the production Web schema",
  ).toBe(true);
});
