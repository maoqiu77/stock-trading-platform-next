import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_TRADING_DATA,
  formatTradeNumberInput,
  normalizeTradeInput,
  parseTradeNumberInput,
  removeTrackedTicker,
  replaceStockPool,
  upsertPositionPlan,
  type TradingDataState,
} from "./trading-data.ts";

function testState(): TradingDataState {
  return {
    ...DEFAULT_TRADING_DATA,
    stockPool: ["VOO"],
    positions: [
      {
        ticker: "VOO",
        targetWeight: 0.2,
        assetType: "ETF",
        takeProfitPct: 0.1,
        stopLossPct: 0.05,
        purchaseDate: "",
      },
    ],
    trades: [],
  };
}

test("upsertPositionPlan adds a new target ticker to the stock pool", () => {
  const next = upsertPositionPlan(testState(), {
    ticker: "dram",
    targetWeight: 0.1,
    assetType: "STOCK",
    takeProfitPct: 0.2,
    stopLossPct: 0.08,
    purchaseDate: "",
  });

  assert.deepEqual(next.stockPool, ["VOO", "DRAM"]);
  assert.equal(next.positions.at(-1)?.ticker, "DRAM");
});

test("removeTrackedTicker removes a ticker from positions and stock pool", () => {
  const withDram = upsertPositionPlan(testState(), {
    ticker: "DRAM",
    targetWeight: 0.1,
    assetType: "STOCK",
    takeProfitPct: 0.2,
    stopLossPct: 0.08,
    purchaseDate: "",
  });

  const next = removeTrackedTicker(withDram, "dram");

  assert.deepEqual(next.stockPool, ["VOO"]);
  assert.deepEqual(
    next.positions.map((position) => position.ticker),
    ["VOO"]
  );
});

test("replaceStockPool removes position targets for deleted pool tickers", () => {
  const withDram = upsertPositionPlan(testState(), {
    ticker: "DRAM",
    targetWeight: 0.1,
    assetType: "STOCK",
    takeProfitPct: 0.2,
    stopLossPct: 0.08,
    purchaseDate: "",
  });

  const next = replaceStockPool(withDram, "DRAM");

  assert.deepEqual(next.stockPool, ["DRAM"]);
  assert.deepEqual(
    next.positions.map((position) => position.ticker),
    ["DRAM"]
  );
});

test("normalizeTradeInput keeps trade amount and unit price to four decimals", () => {
  const trade = normalizeTradeInput({
    date: "2026-06-16",
    ticker: "SMCI",
    action: "买入",
    unitPrice: 48.12345,
    amount: 120.98765,
    note: "decimal precision",
  });

  assert.equal(trade.unitPrice, 48.1235);
  assert.equal(trade.amount, 120.9877);
});

test("trade number input helpers show empty values for zero and parse blanks as zero", () => {
  assert.equal(formatTradeNumberInput(0), "");
  assert.equal(formatTradeNumberInput(12.34567), "12.3457");
  assert.equal(parseTradeNumberInput(""), 0);
  assert.equal(parseTradeNumberInput("0.1234"), 0.1234);
});
