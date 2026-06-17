import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(
  new URL("./platform-workspace.tsx", import.meta.url),
  "utf-8"
);

test("platform workspace lazy-loads non-overview views", () => {
  assert.match(source, /from "next\/dynamic"/);
  assert.doesNotMatch(
    source,
    /import \{ ChartWorkspace \} from "@\/features\/charts\/chart-workspace"/
  );
  assert.doesNotMatch(
    source,
    /import \{ StrategyView \} from "@\/features\/platform\/views\/strategy-view"/
  );
  assert.doesNotMatch(
    source,
    /import \{ AiAdviceView \} from "@\/features\/platform\/views\/ai-advice-view"/
  );
  assert.doesNotMatch(
    source,
    /import \{ DataManagementView \} from "@\/features\/platform\/views\/data-management-view"/
  );
  assert.doesNotMatch(
    source,
    /import \{ SettingsView \} from "@\/features\/platform\/views\/settings-view"/
  );
});
