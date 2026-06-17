from __future__ import annotations

import unittest

from pydantic import ValidationError
from typing import Any, get_type_hints


class ApiContractTest(unittest.TestCase):
    def test_ai_chat_rejects_non_string_prompt(self) -> None:
        models = self.load_request_models()

        with self.assertRaises(ValidationError):
            models["AiAdviceChatRequest"].model_validate({"prompt": 123})

    def test_ai_generate_rejects_non_string_brief(self) -> None:
        models = self.load_request_models()

        with self.assertRaises(ValidationError):
            models["AiAdviceBriefRequest"].model_validate({"brief": 123})

    def test_ai_settings_rejects_non_string_fields(self) -> None:
        models = self.load_request_models()

        with self.assertRaises(ValidationError):
            models["AiSettingsUpdateRequest"].model_validate(
                {"baseUrl": 123, "model": "gpt-test", "apiKey": "sk-test"}
            )

    def test_ai_routes_use_request_models(self) -> None:
        from app import main

        models = self.load_request_models()

        self.assertIs(
            get_type_hints(main.generate_ai_advice)["payload"],
            models["AiAdviceBriefRequest"],
        )
        self.assertIs(
            get_type_hints(main.ai_advice_chat)["payload"],
            models["AiAdviceChatRequest"],
        )
        self.assertIs(
            get_type_hints(main.put_ai_settings)["payload"],
            models["AiSettingsUpdateRequest"],
        )
        self.assertIs(
            get_type_hints(main.test_ai_settings)["payload"],
            models["AiSettingsTestRequest"],
        )

    def load_request_models(self) -> dict[str, Any]:
        try:
            from app.api_models import (
                AiAdviceBriefRequest,
                AiAdviceChatRequest,
                AiSettingsTestRequest,
                AiSettingsUpdateRequest,
            )
        except ImportError as exc:
            self.fail(f"request models are missing: {exc}")
        return {
            "AiAdviceBriefRequest": AiAdviceBriefRequest,
            "AiAdviceChatRequest": AiAdviceChatRequest,
            "AiSettingsTestRequest": AiSettingsTestRequest,
            "AiSettingsUpdateRequest": AiSettingsUpdateRequest,
        }


if __name__ == "__main__":
    unittest.main()
