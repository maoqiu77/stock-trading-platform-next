from __future__ import annotations

import unittest

from app.modules import ai_advice


class AiAdvicePromptTest(unittest.TestCase):
    def test_external_prompt_includes_layered_framework_and_strategy_roles(self) -> None:
        settings = {
            "etfPullbackMin": 0.02,
            "etfPullbackMax": 0.08,
            "etfDeeperPullbackMin": 0.08,
            "etfDeeperPullbackMax": 0.15,
            "etfRsiMax": 74,
            "etfTakeProfitRsi": 84,
            "corePullbackMin": 0.03,
            "corePullbackMax": 0.10,
            "coreDeeperPullbackMin": 0.10,
            "coreDeeperPullbackMax": 0.18,
            "coreRsiMax": 72,
            "coreTakeProfitRsi": 82,
            "satellitePullbackMin": 0.05,
            "satellitePullbackMax": 0.14,
            "satelliteDeeperPullbackMin": 0.14,
            "satelliteDeeperPullbackMax": 0.24,
            "satelliteRsiMax": 68,
            "satelliteTakeProfitRsi": 78,
            "hardStopMaBreakRatio": 0.5,
            "coreHoldings": {"NVDA": "core", "MRVL": "satellite"},
            "satelliteSymbols": ["MRVL"],
        }
        prompt = ai_advice.build_external_advice_prompt(
            brief="",
            summary={"totalAssets": 10000.0, "holdingCost": 3000.0, "cash": 7000.0},
            state={"account": {}, "trades": []},
            positions=[
                {
                    "ticker": "QQQM",
                    "assetType": "ETF",
                    "targetWeight": 0.35,
                    "shares": 3,
                    "costBasis": 200,
                },
                {
                    "ticker": "MRVL",
                    "assetType": "STOCK",
                    "targetWeight": 0.05,
                    "shares": 5,
                    "costBasis": 60,
                },
            ],
            settings=settings,
            strategy_config={"core_holdings": {"NVDA": "core", "MRVL": "satellite"}},
            risk_config={"max_etf_weight": 0.6},
            quotes=[{"ticker": "MRVL", "price": 65, "source": "yahoo"}],
            signals=[],
            intraday_context=[],
            news_items=[],
            context={"beijing_time": "2026-06-16 21:45"},
        )

        self.assertIn("你必须先理解并持续遵守以下投资框架", prompt)
        self.assertIn("核心 ETF", prompt)
        self.assertIn("核心科技仓", prompt)
        self.assertIn("卫星仓波动更大", prompt)
        self.assertIn('"strategy_role": "core etf"', prompt)
        self.assertIn('"strategy_role": "satellite"', prompt)
        self.assertIn("当前分层策略摘要", prompt)
        self.assertIn("当前持仓快照（已补充策略角色）", prompt)

    def test_intraday_summary_exposes_timing_levels(self) -> None:
        chart = {"range": "1d", "interval": "5m", "source": "yahoo"}
        bars = [
            {"time": "2026-06-16T13:30:00Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10},
            {"time": "2026-06-16T13:35:00Z", "open": 100, "high": 103, "low": 100, "close": 102, "volume": 20},
            {"time": "2026-06-16T13:40:00Z", "open": 102, "high": 104, "low": 101, "close": 103, "volume": 30},
            {"time": "2026-06-16T13:45:00Z", "open": 103, "high": 105, "low": 102, "close": 104, "volume": 40},
            {"time": "2026-06-16T13:50:00Z", "open": 104, "high": 106, "low": 103, "close": 105, "volume": 50},
            {"time": "2026-06-16T13:55:00Z", "open": 105, "high": 107, "low": 104, "close": 106, "volume": 60},
        ]

        row = ai_advice.summarize_intraday_bars("NVDA", chart, bars)

        self.assertEqual(row["support_levels"], [104, 103, 99])
        self.assertEqual(row["resistance_levels"], [107, 106, 105])
        self.assertEqual(row["key_observation_price"], 104)
        self.assertEqual(row["entry_timing"], "等待回踩")
        self.assertIn("站稳", row["bullish_scenario"])
        self.assertIn("跌破", row["bearish_scenario"])


if __name__ == "__main__":
    unittest.main()
