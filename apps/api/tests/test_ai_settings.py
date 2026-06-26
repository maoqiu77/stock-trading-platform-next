from __future__ import annotations

import unittest
from unittest.mock import patch

import requests
from fastapi import HTTPException

from app.modules import ai_settings


class AiSettingsTest(unittest.TestCase):
    def test_connection_test_checks_responses_api(self) -> None:
        responses = [
            FakeResponse({"data": [{"id": "gpt-test"}]}),
            FakeResponse(
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
        ]

        with (
            patch.object(ai_settings, "load_ai_settings", return_value={}),
            patch.object(requests, "get", return_value=responses[0]) as get,
            patch.object(requests, "post", return_value=responses[1]) as post,
        ):
            result = ai_settings.test_ai_settings_connection(
                {
                    "baseUrl": "https://example.test/v1",
                    "model": "gpt-test",
                    "apiKey": "sk-test",
                }
            )

        get.assert_called_once()
        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], "https://example.test/v1/responses")
        self.assertTrue(result["responsesOk"])
        self.assertEqual(result["generationEndpoint"], "responses")
        self.assertIn("Responses API 可用", result["message"])

    def test_connection_test_falls_back_to_chat_completions(self) -> None:
        responses = [
            FakeResponse({"data": [{"id": "gpt-test"}]}),
            FakeResponse(
                {"error": "unsupported"},
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
        ]

        with (
            patch.object(ai_settings, "load_ai_settings", return_value={}),
            patch.object(requests, "get", return_value=responses[0]),
            patch.object(requests, "post", side_effect=responses[1:]) as post,
        ):
            result = ai_settings.test_ai_settings_connection(
                {
                    "baseUrl": "https://example.test/v1",
                    "model": "gpt-test",
                    "apiKey": "sk-test",
                }
            )

        self.assertEqual(
            [call.args[0] for call in post.call_args_list],
            [
                "https://example.test/v1/responses",
                "https://example.test/v1/chat/completions",
            ],
        )
        self.assertEqual(result["generationEndpoint"], "chat/completions")
        self.assertIn("chat/completions API 可用", result["message"])

    def test_connection_test_continues_when_models_endpoint_is_blocked(self) -> None:
        with (
            patch.object(ai_settings, "load_ai_settings", return_value={}),
            patch.object(
                requests,
                "get",
                return_value=FakeResponse(
                    {"error": "blocked"},
                    status_code=403,
                    reason="Forbidden",
                ),
            ),
            patch.object(
                requests,
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
            result = ai_settings.test_ai_settings_connection(
                {
                    "baseUrl": "https://example.test/v1",
                    "model": "gpt-test",
                    "apiKey": "sk-test",
                }
            )

        self.assertEqual(result["generationEndpoint"], "responses")
        self.assertIsNone(result["modelMatched"])
        self.assertIn("/models 测试失败", result["message"])
        self.assertEqual(post.call_count, 1)

    def test_connection_test_fails_when_responses_api_is_unavailable(self) -> None:
        with (
            patch.object(ai_settings, "load_ai_settings", return_value={}),
            patch.object(
                requests,
                "get",
                return_value=FakeResponse({"data": [{"id": "gpt-test"}]}),
            ),
            patch.object(
                requests,
                "post",
                side_effect=[
                    FakeResponse(
                        {"error": "unavailable"},
                        status_code=503,
                        reason="Service Unavailable",
                    ),
                    FakeResponse(
                        {"error": "unavailable"},
                        status_code=503,
                        reason="Service Unavailable",
                    ),
                ],
            ) as post,
        ):
            with self.assertRaises(HTTPException) as context:
                ai_settings.test_ai_settings_connection(
                    {
                        "baseUrl": "https://example.test/v1",
                        "model": "gpt-test",
                        "apiKey": "sk-test",
                    }
                )

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("AI 生成接口测试失败", str(context.exception.detail))
        self.assertIn("503", str(context.exception.detail))
        self.assertEqual(
            [call.args[0] for call in post.call_args_list],
            [
                "https://example.test/v1/responses",
                "https://example.test/v1/chat/completions",
            ],
        )

    def test_connection_test_includes_provider_error_message(self) -> None:
        with (
            patch.object(ai_settings, "load_ai_settings", return_value={}),
            patch.object(
                requests,
                "get",
                return_value=FakeResponse({"data": [{"id": "gpt-test"}]}),
            ),
            patch.object(
                requests,
                "post",
                side_effect=[
                    FakeResponse(
                        {
                            "error": {
                                "message": "Client not allowed (detected: python-requests/2.32.5)"
                            }
                        },
                        status_code=400,
                        reason="Bad Request",
                    ),
                    FakeResponse(
                        {
                            "error": {
                                "message": "Client not allowed (detected: python-requests/2.32.5)"
                            }
                        },
                        status_code=400,
                        reason="Bad Request",
                    ),
                ],
            ),
        ):
            with self.assertRaises(HTTPException) as context:
                ai_settings.test_ai_settings_connection(
                    {
                        "baseUrl": "https://example.test/v1",
                        "model": "gpt-test",
                        "apiKey": "sk-test",
                    }
                )

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

    def json(self) -> dict[str, object]:
        return self.payload

    @property
    def text(self) -> str:
        return str(self.payload)


if __name__ == "__main__":
    unittest.main()
