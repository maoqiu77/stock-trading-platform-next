import assert from "node:assert/strict";
import test from "node:test";

import { buildQuotesPath } from "./quote-path.ts";
import { TIMEFRAMES } from "./types.ts";

test("buildQuotesPath includes refresh flag when quotes are force refreshed", () => {
  assert.equal(
    buildQuotesPath(["SMCI", "NVDA"], true),
    "/api/quotes?ticker=SMCI&ticker=NVDA&refresh=1"
  );
});

test("buildQuotesPath omits refresh flag for normal polling", () => {
  assert.equal(buildQuotesPath(["SMCI"], false), "/api/quotes?ticker=SMCI");
});

test("chart timeframes keep day and week candles off monthly history", () => {
  const day = TIMEFRAMES.find((item) => item.key === "D");
  const week = TIMEFRAMES.find((item) => item.key === "W");
  const month = TIMEFRAMES.find((item) => item.key === "M");

  assert.equal(day?.range, "5y");
  assert.equal(day?.interval, "1d");
  assert.equal(week?.range, "10y");
  assert.equal(week?.interval, "1wk");
  assert.equal(month?.range, "10y");
  assert.equal(month?.interval, "1mo");
});
