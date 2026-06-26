from __future__ import annotations

import unittest
from unittest.mock import patch

import requests
from fastapi import HTTPException

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

    def test_sanitized_record_preserves_saved_prompt(self) -> None:
        record = ai_advice.sanitize_ai_advice_record(
            {
                "date": "2026-06-16",
                "generated_at": "2026-06-16 21:45",
                "content": "生成时间：2026-06-16 21:45",
                "prompt": "发送给 AI 的上下文",
                "messages": [],
                "beijing_context": {},
                "news": [],
                "source": "external-ai",
            }
        )

        self.assertEqual(record["prompt"], "发送给 AI 的上下文")

    def test_call_ai_response_uses_responses_api(self) -> None:
        with (
            patch.object(
                ai_advice,
                "load_ai_settings",
                return_value={
                    "baseUrl": "https://example.test/v1",
                    "model": "gpt-test",
                    "apiKey": "sk-test",
                },
            ),
            patch.object(
                ai_advice.requests,
                "post",
                return_value=FakeResponse(
                    {
                        "output": [
                            {
                                "type": "message",
                                "role": "assistant",
                                "content": [{"type": "output_text", "text": "ok"}],
                            }
                        ]
                    }
                ),
            ) as post,
        ):
            content = ai_advice.call_ai_response(
                [
                    {"role": "system", "content": "system rules"},
                    {"role": "user", "content": "user prompt"},
                ]
            )

        self.assertEqual(content, "ok")
        self.assertEqual(post.call_args.args[0], "https://example.test/v1/responses")
        self.assertEqual(post.call_args.kwargs["json"]["instructions"], "system rules")
        self.assertEqual(post.call_args.kwargs["json"]["input"], [{"role": "user", "content": "user prompt"}])

    def test_call_ai_response_falls_back_to_chat_completions(self) -> None:
        with (
            patch.object(
                ai_advice,
                "load_ai_settings",
                return_value={
                    "baseUrl": "https://example.test/v1",
                    "model": "gpt-test",
                    "apiKey": "sk-test",
                },
            ),
            patch.object(
                ai_advice.requests,
                "post",
                side_effect=[
                    FakeResponse(
                        {"error": "blocked"},
                        status_code=403,
                        reason="Forbidden",
                    ),
                    FakeResponse(
                        {
                            "choices": [
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": "ok",
                                    }
                                }
                            ]
                        }
                    ),
                ],
            ) as post,
        ):
            content = ai_advice.call_ai_response(
                [
                    {"role": "system", "content": "system rules"},
                    {"role": "user", "content": "user prompt"},
                ]
            )

        self.assertEqual(content, "ok")
        self.assertEqual(
            [call.args[0] for call in post.call_args_list],
            [
                "https://example.test/v1/responses",
                "https://example.test/v1/chat/completions",
            ],
        )
        self.assertEqual(
            post.call_args.kwargs["json"]["messages"],
            [
                {"role": "system", "content": "system rules"},
                {"role": "user", "content": "user prompt"},
            ],
        )

    def test_call_ai_response_includes_provider_error_message(self) -> None:
        with (
            patch.object(
                ai_advice,
                "load_ai_settings",
                return_value={
                    "baseUrl": "https://example.test/v1",
                    "model": "gpt-test",
                    "apiKey": "sk-test",
                },
            ),
            patch.object(
                ai_advice.requests,
                "post",
                return_value=FakeResponse(
                    {
                        "error": {
                            "message": "Client not allowed (detected: python-requests/2.32.5)"
                        }
                    },
                    status_code=400,
                    reason="Bad Request",
                ),
            ),
        ):
            with self.assertRaises(HTTPException) as context:
                ai_advice.call_ai_response([{"role": "user", "content": "user prompt"}])

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("Client not allowed", str(context.exception.detail))


class FakeResponse:
    def __init__(
        self,
        payload: dict[str, object],
        status_code: int = 200,
        reason: str = "OK",
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.reason = reason

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"{self.status_code} Server Error: {self.reason}",
                response=self,
            )
        return None

    def json(self) -> dict[str, object]:
        return self.payload

    @property
    def text(self) -> str:
        return str(self.payload)


if __name__ == "__main__":
    unittest.main()
