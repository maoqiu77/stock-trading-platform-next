from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests
from fastapi import HTTPException

from app.core.database import get_state_payload, set_state_payload


APP_STATE_KEY = "ai_settings_v1"
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
AI_SETTINGS_TEST_TIMEOUT_SECONDS = 20

DEFAULT_AI_SETTINGS: dict[str, Any] = {
    "schemaVersion": 1,
    "baseUrl": "",
    "model": "",
    "apiKey": "",
    "updatedAt": "",
}


def load_ai_settings() -> dict[str, Any]:
    payload = get_state_payload(APP_STATE_KEY)
    if not payload:
        return DEFAULT_AI_SETTINGS.copy()
    try:
        return sanitize_ai_settings(json.loads(payload))
    except (json.JSONDecodeError, TypeError):
        return DEFAULT_AI_SETTINGS.copy()


def save_ai_settings(settings: dict[str, Any]) -> dict[str, Any]:
    sanitized = sanitize_ai_settings(settings)
    if not sanitized["updatedAt"]:
        sanitized["updatedAt"] = beijing_timestamp()
    set_state_payload(APP_STATE_KEY, json.dumps(sanitized, ensure_ascii=False))
    return sanitized


def get_ai_settings_public() -> dict[str, Any]:
    settings = load_ai_settings()
    return public_ai_settings(settings)


def update_ai_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = load_ai_settings()
    next_settings = {
        **current,
        "baseUrl": str(payload.get("baseUrl", current.get("baseUrl", ""))).strip(),
        "model": str(payload.get("model", current.get("model", ""))).strip(),
        "updatedAt": beijing_timestamp(),
    }
    if payload.get("clearApiKey"):
        next_settings["apiKey"] = ""
    elif "apiKey" in payload:
        api_key = str(payload.get("apiKey") or "").strip()
        if api_key:
            next_settings["apiKey"] = api_key
    return public_ai_settings(save_ai_settings(next_settings))


def test_ai_settings_connection(payload: dict[str, Any]) -> dict[str, Any]:
    current = load_ai_settings()
    base_url = str(payload.get("baseUrl") or current.get("baseUrl", "")).strip().rstrip("/")
    model = str(payload.get("model") or current.get("model", "")).strip()
    api_key = str(payload.get("apiKey") or current.get("apiKey", "")).strip()
    if not base_url or not model or not api_key:
        raise HTTPException(status_code=400, detail="请先提供 AI Base URL、模型和 API Key。")

    try:
        response = requests.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=AI_SETTINGS_TEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload_json = response.json()
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"AI 连接测试失败：{exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="AI 连接测试返回的 JSON 格式无效。") from exc

    models = extract_model_ids(payload_json)
    model_matched = model in models if models else None
    if model_matched is False:
        message = "连接成功，但 /models 返回列表中没有当前模型。"
    elif model_matched is True:
        message = "连接成功，当前模型存在。"
    else:
        message = "连接成功，但无法从 /models 返回中读取模型列表。"
    return {
        "ok": True,
        "baseUrl": base_url,
        "model": model,
        "modelMatched": model_matched,
        "modelCount": len(models),
        "message": message,
    }


def public_ai_settings(settings: dict[str, Any]) -> dict[str, Any]:
    api_key = str(settings.get("apiKey", ""))
    return {
        "schemaVersion": 1,
        "baseUrl": str(settings.get("baseUrl", "")),
        "model": str(settings.get("model", "")),
        "hasApiKey": bool(api_key),
        "apiKeyMasked": mask_api_key(api_key),
        "updatedAt": str(settings.get("updatedAt", "")),
    }


def sanitize_ai_settings(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return DEFAULT_AI_SETTINGS.copy()
    return {
        "schemaVersion": 1,
        "baseUrl": str(value.get("baseUrl", "")).strip(),
        "model": str(value.get("model", "")).strip(),
        "apiKey": str(value.get("apiKey", "")).strip(),
        "updatedAt": str(value.get("updatedAt", "")).strip(),
    }


def mask_api_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def beijing_timestamp() -> str:
    return datetime.now(tz=BEIJING_TZ).strftime("%Y-%m-%d %H:%M")


def extract_model_ids(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    ids = []
    for item in data:
        if isinstance(item, dict):
            model_id = str(item.get("id", "")).strip()
            if model_id:
                ids.append(model_id)
    return ids
