from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.modules.ai_advice import (
    create_ai_chat_reply,
    create_external_ai_advice,
    create_local_ai_advice_draft,
    get_ai_advice_calendar,
)
from app.modules.ai_settings import (
    get_ai_settings_public,
    test_ai_settings_connection,
    update_ai_settings,
)
from app.modules.market import get_chart, get_quotes
from app.modules.research import get_backtest_result, get_signal_rows
from app.modules.trading_data import (
    account_summary,
    derive_positions,
    get_effective_watchlist,
    load_trading_state,
    reset_trading_state,
    save_trading_state,
    validate_trading_state,
)


app = FastAPI(title="Stock Trading Platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/watchlist")
def watchlist() -> dict[str, object]:
    return {"items": get_effective_watchlist()}


@app.get("/api/quotes")
def quotes(ticker: list[str] = Query(default=[])) -> dict[str, object]:
    symbols = get_effective_watchlist()
    if ticker:
        wanted = {item.upper() for item in ticker}
        symbols = [item for item in symbols if item["ticker"].upper() in wanted]
    return {"items": get_quotes(symbols)}


@app.get("/api/charts/{ticker}")
def chart(
    ticker: str,
    range_: str = Query(default="1y", alias="range"),
    interval: str = Query(default="1d"),
) -> dict[str, object]:
    return get_chart(ticker, range_, interval)


@app.get("/api/trading-state")
def trading_state() -> dict[str, object]:
    state = load_trading_state()
    return {
        "state": state,
        "derivedPositions": derive_positions(state),
        "accountSummary": account_summary(state),
        "validationIssues": validate_trading_state(state),
    }


@app.put("/api/trading-state")
def update_trading_state(payload: dict[str, Any]) -> dict[str, object]:
    state = save_trading_state(payload)
    return {
        "state": state,
        "derivedPositions": derive_positions(state),
        "accountSummary": account_summary(state),
        "validationIssues": validate_trading_state(state),
    }


@app.post("/api/trading-state/reset")
def reset_state() -> dict[str, object]:
    state = reset_trading_state()
    return {
        "state": state,
        "derivedPositions": derive_positions(state),
        "accountSummary": account_summary(state),
        "validationIssues": validate_trading_state(state),
    }


@app.get("/api/signals")
def signals() -> dict[str, object]:
    return {"items": get_signal_rows()}


@app.get("/api/backtests/{ticker}")
def backtest(
    ticker: str,
    initial_cash: Optional[float] = Query(default=None, alias="initialCash"),
    range_: str = Query(default="10y", alias="range"),
) -> dict[str, object]:
    return get_backtest_result(ticker, initial_cash=initial_cash, range_=range_)


@app.get("/api/ai-advice")
def ai_advice(date: Optional[str] = Query(default=None)) -> dict[str, object]:
    return get_ai_advice_calendar(date)


@app.post("/api/ai-advice/draft")
def create_ai_advice_draft(payload: dict[str, Any]) -> dict[str, object]:
    return create_local_ai_advice_draft(str(payload.get("brief", "")))


@app.post("/api/ai-advice/generate")
def generate_ai_advice(payload: dict[str, Any]) -> dict[str, object]:
    return create_external_ai_advice(str(payload.get("brief", "")))


@app.post("/api/ai-advice/chat")
def ai_advice_chat(payload: dict[str, Any]) -> dict[str, object]:
    return create_ai_chat_reply(str(payload.get("prompt", "")))


@app.get("/api/ai-settings")
def ai_settings() -> dict[str, object]:
    return get_ai_settings_public()


@app.put("/api/ai-settings")
def put_ai_settings(payload: dict[str, Any]) -> dict[str, object]:
    return update_ai_settings(payload)


@app.post("/api/ai-settings/test")
def test_ai_settings(payload: dict[str, Any]) -> dict[str, object]:
    return test_ai_settings_connection(payload)
