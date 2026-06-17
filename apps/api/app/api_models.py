from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr


class TradingStateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")


class AiAdviceBriefRequest(BaseModel):
    brief: StrictStr = ""


class AiAdviceChatRequest(BaseModel):
    prompt: StrictStr


class AiSettingsUpdateRequest(BaseModel):
    baseUrl: Optional[StrictStr] = None
    model: Optional[StrictStr] = None
    apiKey: Optional[StrictStr] = None
    clearApiKey: Optional[StrictBool] = None


class AiSettingsTestRequest(BaseModel):
    baseUrl: Optional[StrictStr] = None
    model: Optional[StrictStr] = None
    apiKey: Optional[StrictStr] = None
