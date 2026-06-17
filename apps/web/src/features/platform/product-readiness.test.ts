import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

function readSource(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf-8");
}

test("platform navigation exposes health checks for end users", () => {
  const source = readSource("./types.ts");

  assert.match(source, /"health"/);
  assert.match(source, /健康检查/);
});

test("workspace includes first-run onboarding without CSV import copy", () => {
  const source = readSource("./platform-workspace.tsx");

  assert.match(source, /stock-platform-onboarding-v1/);
  assert.match(source, /首次使用/);
  assert.match(source, /storage\/local/);
  assert.doesNotMatch(source, /CSV|TSV|导入文件/);
});

test("AI advice view confirms private context before sending to AI", () => {
  const source = readSource("./views/ai-advice-view.tsx");

  assert.match(source, /确认发送给 AI/);
  assert.match(source, /账户/);
  assert.match(source, /持仓/);
  assert.match(source, /交易流水/);
  assert.match(source, /行情与策略信号/);
});
