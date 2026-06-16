import assert from "node:assert/strict";
import test from "node:test";

import { resolveApiBaseUrl } from "./api-base-url.ts";

test("resolveApiBaseUrl defaults to same-origin API requests", () => {
  assert.equal(resolveApiBaseUrl(undefined), "");
});

test("resolveApiBaseUrl trims a configured trailing slash", () => {
  assert.equal(resolveApiBaseUrl("http://localhost:9000/"), "http://localhost:9000");
});
