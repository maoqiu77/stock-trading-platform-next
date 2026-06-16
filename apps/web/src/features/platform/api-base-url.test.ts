import assert from "node:assert/strict";
import test from "node:test";

import { resolveApiBaseUrl } from "./api-base-url.ts";

test("resolveApiBaseUrl defaults to the local FastAPI server", () => {
  assert.equal(resolveApiBaseUrl(undefined), "http://127.0.0.1:8000");
});

test("resolveApiBaseUrl trims a configured trailing slash", () => {
  assert.equal(resolveApiBaseUrl("http://localhost:9000/"), "http://localhost:9000");
});
