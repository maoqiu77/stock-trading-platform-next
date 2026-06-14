from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from fastapi import HTTPException

from app.core.database import get_state_payload, set_state_payload
from app.modules.ai_settings import load_ai_settings
from app.modules.market import get_chart, get_quotes
from app.modules.research import get_signal_rows
from app.modules.trading_data import (
    account_summary,
    active_strategy_settings,
    derive_positions,
    get_effective_watchlist,
    load_trading_state,
    strategy_settings_to_engine_config,
)


APP_STATE_KEY = "ai_advice_v1"
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
AI_TIMEOUT_SECONDS = 120


@dataclass
class NewsItem:
    title: str
    source: str
    published: str
    link: str


def load_ai_advice_state() -> dict[str, Any]:
    payload = get_state_payload(APP_STATE_KEY)
    if not payload:
        return {"schemaVersion": 1, "records": {}}
    try:
        return sanitize_ai_advice_state(json.loads(payload))
    except (json.JSONDecodeError, TypeError):
        return {"schemaVersion": 1, "records": {}}


def save_ai_advice_state(state: dict[str, Any]) -> dict[str, Any]:
    sanitized = sanitize_ai_advice_state(state)
    set_state_payload(APP_STATE_KEY, json.dumps(sanitized, ensure_ascii=False))
    return sanitized


def list_ai_advice_dates() -> list[str]:
    state = load_ai_advice_state()
    return sorted(state["records"].keys())


def get_ai_advice_record(target_date: str | None = None) -> dict[str, Any] | None:
    state = load_ai_advice_state()
    if target_date:
        return state["records"].get(target_date)
    dates = sorted(state["records"].keys())
    return state["records"].get(dates[-1]) if dates else None


def get_ai_advice_calendar(target_date: str | None = None) -> dict[str, Any]:
    now_context = beijing_now_context()
    saved_dates = list_ai_advice_dates()
    selected_date = select_ai_advice_date(saved_dates, now_context["beijing_date"], target_date)
    return {
        "today": now_context["beijing_date"],
        "selectedDate": selected_date,
        "dates": saved_dates,
        "record": get_ai_advice_record(selected_date) if selected_date else None,
    }


def create_local_ai_advice_draft(brief: str = "") -> dict[str, Any]:
    context = beijing_now_context()
    target_date = context["beijing_date"]
    state = load_trading_state()
    summary = account_summary(state)
    positions = derive_positions(state)
    settings = active_strategy_settings(state)
    signals = get_signal_rows()
    content = build_local_advice_content(brief, summary, positions, settings, signals, context)
    record = {
        "date": target_date,
        "generated_at": context["beijing_time"],
        "content": content,
        "messages": [
            {
                "role": "assistant",
                "content": content,
                "created_at": context["beijing_time"],
            }
        ],
        "beijing_context": context,
        "extra_question": brief.strip(),
        "news": [],
        "source": "local-draft",
    }
    advice_state = load_ai_advice_state()
    advice_state["records"][target_date] = sanitize_ai_advice_record(record)
    save_ai_advice_state(advice_state)
    return get_ai_advice_calendar(target_date)


def create_external_ai_advice(brief: str = "") -> dict[str, Any]:
    state = load_trading_state()
    ensure_external_ai_allowed(state)
    context = beijing_now_context()
    target_date = context["beijing_date"]
    summary = account_summary(state)
    positions = derive_positions(state)
    settings = active_strategy_settings(state)
    strategy_config, risk_config = strategy_settings_to_engine_config(settings)
    signals = get_signal_rows()
    watchlist = get_effective_watchlist()
    quotes = get_quotes(watchlist)
    intraday_context = build_intraday_market_context(watchlist)
    news_items = fetch_yahoo_finance_news(state.get("stockPool", []))
    content = call_chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "你是一个谨慎的美股半自动量化加减仓助手。你不能下单，不能承诺收益，"
                    "不能建议融资、期权、做空或杠杆。平台量化信号是重要输入，但你可以覆盖平台信号，"
                    "前提是必须解释依据。必须纳入账户、持仓、交易记录、止盈止损、趋势、均线、RSI、回撤、"
                    "日内走势摘要、最近约 3 天新闻标题和北京时间交易时段。若行情报价、日内走势或量化信号的"
                    "source 为 sample，必须明确说明实时行情不可用，不得把 sample 价格、MA、RSI 或信号当作真实依据。"
                    "输出中文，简洁清楚，适合用户手动确认。"
                ),
            },
            {
                "role": "user",
                "content": build_external_advice_prompt(
                    brief=brief,
                    summary=summary,
                    state=state,
                    positions=positions,
                    settings=settings,
                    strategy_config=strategy_config,
                    risk_config=risk_config,
                    quotes=quotes,
                    signals=signals,
                    intraday_context=intraday_context,
                    news_items=news_items,
                    context=context,
                ),
            },
        ]
    )
    generated_at = context["beijing_time"]
    if not content.lstrip().startswith("生成时间："):
        content = f"生成时间：{generated_at}（北京时间）\n\n{content}"
    record = {
        "date": target_date,
        "generated_at": generated_at,
        "content": content,
        "messages": [
            {
                "role": "assistant",
                "content": content,
                "created_at": generated_at,
            }
        ],
        "beijing_context": context,
        "extra_question": brief.strip(),
        "news": [news_item_to_dict(item) for item in news_items],
        "source": "external-ai",
    }
    advice_state = load_ai_advice_state()
    advice_state["records"][target_date] = sanitize_ai_advice_record(record)
    save_ai_advice_state(advice_state)
    return get_ai_advice_calendar(target_date)


def create_ai_chat_reply(prompt: str) -> dict[str, Any]:
    clean_prompt = prompt.strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="请输入要追问 AI 的问题。")

    state = load_trading_state()
    ensure_external_ai_allowed(state)
    context = beijing_now_context()
    target_date = context["beijing_date"]
    current_record = get_ai_advice_record(target_date)
    if not current_record or not current_record.get("messages"):
        raise HTTPException(status_code=409, detail="请先生成今日 AI 综合建议，再继续追问。")

    summary = account_summary(state)
    positions = derive_positions(state)
    settings = active_strategy_settings(state)
    strategy_config, risk_config = strategy_settings_to_engine_config(settings)
    signals = get_signal_rows()
    watchlist = get_effective_watchlist()
    quotes = get_quotes(watchlist)
    intraday_context = build_intraday_market_context(watchlist)
    news_items = fetch_yahoo_finance_news(state.get("stockPool", []))
    user_message = {
        "role": "user",
        "content": clean_prompt,
        "created_at": context["beijing_time"],
    }
    chat_history = normalize_conversation_messages(
        [*current_record.get("messages", []), user_message]
    )
    reply = call_chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "你是一个谨慎的美股半自动量化加减仓聊天助手。你不能下单，不能承诺收益，"
                    "不能建议融资、期权、做空或杠杆。优先回答用户最新问题，不要每次重复完整日报。"
                    "只能基于系统提供的账户、持仓、交易、信号和新闻标题上下文回答；新闻不足时要说明不足。"
                    "若行情报价、日内走势或量化信号的 source 为 sample，必须说明实时行情不可用，"
                    "不得把 sample 价格、MA、RSI 或信号当作真实依据。"
                ),
            },
            {
                "role": "user",
                "content": build_chat_context_prompt(
                    summary=summary,
                    state=state,
                    positions=positions,
                    settings=settings,
                    strategy_config=strategy_config,
                    risk_config=risk_config,
                    quotes=quotes,
                    signals=signals,
                    intraday_context=intraday_context,
                    news_items=news_items,
                    context=context,
                ),
            },
            *chat_history[-10:],
        ]
    )
    assistant_message = {
        "role": "assistant",
        "content": reply,
        "created_at": context["beijing_time"],
    }
    updated_record = {
        **current_record,
        "generated_at": context["beijing_time"],
        "messages": [*current_record.get("messages", []), user_message, assistant_message],
        "beijing_context": context,
        "news": [news_item_to_dict(item) for item in news_items],
        "source": "external-ai",
    }
    advice_state = load_ai_advice_state()
    advice_state["records"][target_date] = sanitize_ai_advice_record(updated_record)
    save_ai_advice_state(advice_state)
    return get_ai_advice_calendar(target_date)


def build_local_advice_content(
    brief: str,
    summary: dict[str, float],
    positions: list[dict[str, Any]],
    settings: dict[str, Any],
    signals: list[dict[str, Any]],
    context: dict[str, str],
) -> str:
    actionable = [
        signal
        for signal in signals
        if signal.get("action") and not str(signal["action"]).startswith("不")
    ]
    watched = signals[:5]
    lines = [
        f"生成时间：{context['beijing_time']}（北京时间）",
        "",
        "## 本地 AI 日历草案",
        "",
        brief.strip() or "研究目标：根据本地账户、持仓、信号和策略参数生成今日复盘草案。",
        "",
        "## 账户摘要",
        "",
        f"- 总资产：${summary['totalAssets']:,.2f}",
        f"- 持仓成本：${summary['holdingCost']:,.2f}",
        f"- 推算现金：${summary['cash']:,.2f}",
        f"- 持仓目标数量：{len(positions)}",
        "",
        "## 策略参数",
        "",
        f"- RSI 周期：{int(number(settings.get('rsiPeriod'), 14))}",
        f"- 加仓 RSI 上限：{number(settings.get('rsiMax'), 72):.0f}",
        f"- 普通回撤区间：{number(settings.get('pullbackMin'), 0.03):.0%}-{number(settings.get('pullbackMax'), 0.10):.0%}",
        f"- 深回撤区间：{number(settings.get('deeperPullbackMin'), 0.10):.0%}-{number(settings.get('deeperPullbackMax'), 0.18):.0%}",
        f"- 单次加仓上限：总资产 {number(settings.get('singleAddAssetRatio'), 0.05):.0%} / 现金 {number(settings.get('singleAddCashRatio'), 0.20):.0%}",
        "",
        "## 今日信号",
        "",
    ]
    if watched:
        for signal in watched:
            reason = signal.get("reasons") or signal.get("blocked_reasons") or signal.get("risk_notes") or ""
            lines.append(
                f"- {signal.get('ticker', '')}: {signal.get('action', '')} / {signal.get('status', '')}，"
                f"建议金额 ${number(signal.get('suggested_amount')):,.2f}。{reason}"
            )
    else:
        lines.append("- 暂无信号数据。")
    lines.extend(
        [
            "",
            "## 执行提醒",
            "",
            f"- 当前交易时段判断：{context['estimated_session_status']}",
            f"- 操作节奏：{context['timing_suggestion']}",
            "- 本地草案不调用外部模型，不包含联网新闻；接入 OpenAI-compatible 服务后可复用同一条日历记录结构。",
        ]
    )
    if actionable:
        lines.extend(
            [
                "",
                "## 需要重点复核",
                "",
            ]
        )
        for signal in actionable:
            lines.append(f"- {signal.get('manual_instruction', '')}")
    return "\n".join(lines)


def ensure_external_ai_allowed(state: dict[str, Any]) -> None:
    ai_settings = load_ai_settings()
    if not ai_settings.get("apiKey") or not ai_settings.get("baseUrl") or not ai_settings.get("model"):
        raise HTTPException(status_code=400, detail="请先在数据管理配置 AI Base URL、模型和 API Key。")


def call_chat_completion(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    ai_settings = load_ai_settings()
    api_key = str(ai_settings.get("apiKey", "")).strip()
    base_url = str(ai_settings.get("baseUrl", "")).strip().rstrip("/")
    model = str(ai_settings.get("model", "")).strip()
    if not api_key or not base_url or not model:
        raise HTTPException(status_code=400, detail="AI 设置不完整。")
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "messages": messages, "temperature": temperature},
            timeout=AI_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"]).strip()
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"AI 接口请求失败：{exc}") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="AI 接口返回格式不符合 chat/completions。") from exc


def build_external_advice_prompt(
    *,
    brief: str,
    summary: dict[str, float],
    state: dict[str, Any],
    positions: list[dict[str, Any]],
    settings: dict[str, Any],
    strategy_config: dict[str, Any],
    risk_config: dict[str, Any],
    quotes: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    intraday_context: list[dict[str, Any]],
    news_items: list[NewsItem],
    context: dict[str, str],
) -> str:
    return f"""
请基于以下完整上下文，给出今天的最终手动加仓/减仓建议。你是最终决策助手，平台量化信号是重要输入，但不是最高裁判。

输出要求：
1. 开头第一行必须写：生成时间：YYYY-MM-DD HH:MM（北京时间）。
2. 第二部分写“今日最终结论”，用 1-3 句话说明今天应不应该操作、优先操作哪些标的。
3. 如果“用户额外问题”不为空，请立即新增“额外问题回答”一节。
4. 给出“账户总体判断”：现金、仓位是否激进、是否需要调整策略参数，控制在 3-5 行。
5. 给出“标的决策表”：标的 / 分类 / 平台信号 / AI 最终动作 / 金额或股数 / 一句话理由。
6. 对需要操作、平台与 AI 不一致、止盈止损触发、新闻风险明显的标的，在“重点说明”里展开。
7. 建仓和加仓必须分批；必须结合“日内走势摘要”判断现在小额、等待回踩、分批还是暂不动；不允许一次性打满目标仓位。
8. 若价格跌破 MA120、触发止损线、仓位明显高于目标或 RSI 过热，必须优先讨论减仓或降温。
9. 结合当前北京时间，提醒是现在执行还是等北京时间 21:30 后再确认。
10. 结尾补“执行顺序建议”，只列今晚最重要的 1-3 个动作。
11. 最后补“策略反馈”，没有问题就写“暂无需要调整的策略问题”。

用户额外问题：
{brief.strip() or '无'}

北京时间上下文：
{json.dumps(context, ensure_ascii=False, indent=2)}

账户摘要：
{json.dumps(summary, ensure_ascii=False, indent=2)}

账户设置：
{json.dumps(state.get("account", {}), ensure_ascii=False, indent=2)}

当前持仓快照：
{json.dumps(positions, ensure_ascii=False, indent=2)}

交易流水：
{json.dumps(state.get("trades", []), ensure_ascii=False, indent=2)}

策略参数：
{json.dumps(settings, ensure_ascii=False, indent=2)}

旧引擎参数：
{json.dumps(strategy_config, ensure_ascii=False, indent=2)}

风控参数：
{json.dumps(risk_config, ensure_ascii=False, indent=2)}

行情报价：
{json.dumps(quotes, ensure_ascii=False, indent=2)}

日内走势摘要：
{json.dumps(intraday_context, ensure_ascii=False, indent=2)}

量化加减仓信号：
{json.dumps(signals, ensure_ascii=False, indent=2)}

最近约 3 天 Yahoo Finance 新闻标题：
{json.dumps([news_item_to_dict(item) for item in news_items], ensure_ascii=False, indent=2)}
"""


def build_chat_context_prompt(
    *,
    summary: dict[str, float],
    state: dict[str, Any],
    positions: list[dict[str, Any]],
    settings: dict[str, Any],
    strategy_config: dict[str, Any],
    risk_config: dict[str, Any],
    quotes: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    intraday_context: list[dict[str, Any]],
    news_items: list[NewsItem],
    context: dict[str, str],
) -> str:
    return f"""
以下是当前账户、持仓、买卖操作、行情指标、量化信号和联网抓取的新闻标题上下文。
请先理解这些上下文，然后只回答后续对话里用户最新提出的问题。

北京时间上下文：
{json.dumps(context, ensure_ascii=False, indent=2)}

账户摘要：
{json.dumps(summary, ensure_ascii=False, indent=2)}

当前持仓快照：
{json.dumps(positions, ensure_ascii=False, indent=2)}

买卖操作记录：
{json.dumps(state.get("trades", []), ensure_ascii=False, indent=2)}

策略参数：
{json.dumps(settings, ensure_ascii=False, indent=2)}

旧引擎参数：
{json.dumps(strategy_config, ensure_ascii=False, indent=2)}

风控参数：
{json.dumps(risk_config, ensure_ascii=False, indent=2)}

行情报价：
{json.dumps(quotes, ensure_ascii=False, indent=2)}

日内走势摘要：
{json.dumps(intraday_context, ensure_ascii=False, indent=2)}

量化加减仓信号：
{json.dumps(signals, ensure_ascii=False, indent=2)}

最近约 3 天 Yahoo Finance 新闻标题：
{json.dumps([news_item_to_dict(item) for item in news_items], ensure_ascii=False, indent=2)}
"""


def build_intraday_market_context(watchlist: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tickers = [
        str(item.get("ticker", "")).upper().strip()
        for item in watchlist
        if str(item.get("ticker", "")).strip()
    ]
    if not tickers:
        return []

    max_workers = min(len(tickers), 6)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        rows = list(executor.map(build_intraday_row, tickers))
    return [row for row in rows if row]


def build_intraday_row(ticker: str) -> dict[str, Any] | None:
    try:
        chart = get_chart(ticker, "1d", "5m")
    except Exception:
        return None
    bars = chart.get("bars", [])
    if not isinstance(bars, list) or not bars:
        return None
    return summarize_intraday_bars(ticker, chart, bars)


def summarize_intraday_bars(
    ticker: str,
    chart: dict[str, Any],
    bars: list[dict[str, Any]],
) -> dict[str, Any]:
    first = bars[0]
    last = bars[-1]
    open_price = number(first.get("open"))
    latest_price = number(last.get("close"))
    highs = [number(bar.get("high")) for bar in bars]
    lows = [number(bar.get("low")) for bar in bars]
    closes = [number(bar.get("close")) for bar in bars]
    volumes = [number(bar.get("volume")) for bar in bars]
    high = max(highs) if highs else 0.0
    low = min(lows) if lows else 0.0
    change = latest_price - open_price
    change_pct = change / open_price if open_price else 0.0
    range_position = (latest_price - low) / (high - low) if high > low else 0.0
    recent_closes = closes[-6:]
    recent_change = recent_closes[-1] - recent_closes[0] if len(recent_closes) >= 2 else 0.0
    recent_change_pct = recent_change / recent_closes[0] if len(recent_closes) >= 2 and recent_closes[0] else 0.0
    return {
        "ticker": ticker,
        "range": chart.get("range"),
        "interval": chart.get("interval"),
        "source": chart.get("source"),
        "bar_count": len(bars),
        "open": round(open_price, 4),
        "latest": round(latest_price, 4),
        "high": round(high, 4),
        "low": round(low, 4),
        "change_pct": round(change_pct, 4),
        "range_position": round(range_position, 4),
        "recent_30m_change_pct": round(recent_change_pct, 4),
        "volume": int(sum(volumes)),
        "last_bar_time": str(last.get("time", "")),
    }


def fetch_yahoo_finance_news(
    tickers: list[str],
    days: int = 3,
    per_day: int = 4,
) -> list[NewsItem]:
    clean = []
    for ticker in tickers:
        symbol = str(ticker).upper().strip()
        if symbol and symbol not in clean:
            clean.append(symbol)

    feeds = [
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        for ticker in clean
    ]
    if clean:
        feeds.insert(
            0,
            f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={','.join(clean)}&region=US&lang=en-US",
        )
    feeds.append("https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EIXIC,%5EGSPC,QQQ&region=US&lang=en-US")

    items: list[NewsItem] = []
    for url in feeds:
        try:
            items.extend(parse_news_feed(url))
        except Exception:
            continue
    deduped: list[NewsItem] = []
    seen = set()
    for item in items:
        key = item.title.lower()
        if key not in seen:
            deduped.append(item)
            seen.add(key)
    return select_recent_news_by_day(deduped, days=days, per_day=per_day)


def parse_news_feed(url: str) -> list[NewsItem]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    response.raise_for_status()
    root = ElementTree.fromstring(response.text)
    items = []
    for item in root.findall("./channel/item"):
        title = xml_text(item, "title")
        link = xml_text(item, "link")
        published = format_pub_date(xml_text(item, "pubDate"))
        if title:
            items.append(
                NewsItem(
                    title=title,
                    source="Yahoo Finance",
                    published=published,
                    link=link,
                )
            )
    return items


def select_recent_news_by_day(
    items: list[NewsItem],
    days: int = 3,
    per_day: int = 4,
) -> list[NewsItem]:
    if days <= 0 or per_day <= 0:
        return []
    parsed = [(item, published_date(item.published)) for item in items]
    dated = [(item, item_date) for item, item_date in parsed if item_date is not None]
    if not dated:
        return items[: days * per_day]

    anchor = max(item_date for _, item_date in dated)
    start = anchor - timedelta(days=days - 1)
    groups: dict[date, list[NewsItem]] = defaultdict(list)
    for item, item_date in dated:
        if start <= item_date <= anchor:
            groups[item_date].append(item)

    selected: list[NewsItem] = []
    for offset in range(days):
        day = anchor - timedelta(days=offset)
        selected.extend(groups.get(day, [])[:per_day])
    return selected[: days * per_day]


def normalize_conversation_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized = []
    for message in messages:
        role = str(message.get("role", "")).strip()
        content = str(message.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content})
    return normalized


def news_item_to_dict(item: NewsItem) -> dict[str, str]:
    return {
        "title": item.title,
        "source": item.source,
        "published": item.published,
        "link": item.link,
    }


def xml_text(item: ElementTree.Element, tag: str) -> str:
    found = item.find(tag)
    if found is None or found.text is None:
        return ""
    return unescape(found.text.strip())


def format_pub_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw


def published_date(published: str) -> date | None:
    if not published:
        return None
    try:
        return parsedate_to_datetime(published).date()
    except Exception:
        pass
    try:
        return date.fromisoformat(published[:10])
    except Exception:
        return None


def beijing_now_context() -> dict[str, str]:
    now = pd.Timestamp.now(tz=BEIJING_TZ)
    hour = now.hour + now.minute / 60
    weekday = now.weekday()
    is_weekday = weekday < 5
    if is_weekday and 21.5 <= hour <= 24:
        status = "美股常规交易时段内（按北京时间 21:30-次日 04:00 估算）"
        suggestion = "可以结合券商实时价格再次确认后再手动操作。"
    elif is_weekday and 0 <= hour < 4:
        status = "美股常规交易时段内（按北京时间 21:30-次日 04:00 估算）"
        suggestion = "仍需用券商实时价格确认价格、股数和风险。"
    else:
        status = "美股交易时段外/盘前准备阶段"
        suggestion = "适合生成计划；正式交易建议等 21:30 后再刷新确认。"
    return {
        "beijing_time": now.strftime("%Y-%m-%d %H:%M"),
        "beijing_date": now.date().isoformat(),
        "usual_manual_trade_time": "北京时间 21:30 之后",
        "estimated_session_status": status,
        "timing_suggestion": suggestion,
    }


def select_ai_advice_date(
    saved_dates: list[str],
    default_date: str,
    selected_raw: str | None,
) -> str | None:
    saved = set(saved_dates)
    if selected_raw in saved:
        return selected_raw
    if default_date in saved:
        return default_date
    return saved_dates[-1] if saved_dates else None


def sanitize_ai_advice_state(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"schemaVersion": 1, "records": {}}
    records = value.get("records", {})
    if not isinstance(records, dict):
        records = {}
    return {
        "schemaVersion": 1,
        "records": {
            key: sanitize_ai_advice_record(record)
            for key, record in records.items()
            if is_iso_date(str(key)) and isinstance(record, dict)
        },
    }


def sanitize_ai_advice_record(record: dict[str, Any]) -> dict[str, Any]:
    record_date = str(record.get("date", "")).strip()
    if not is_iso_date(record_date):
        record_date = beijing_now_context()["beijing_date"]
    generated_at = str(record.get("generated_at", "")).strip()
    content = str(record.get("content", "")).strip()
    messages = []
    for message in record.get("messages", []) or []:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).strip()
        message_content = str(message.get("content", "")).strip()
        if role in {"user", "assistant"} and message_content:
            messages.append(
                {
                    "role": role,
                    "content": message_content,
                    "created_at": str(message.get("created_at", generated_at)),
                }
            )
    if not messages and content:
        messages.append({"role": "assistant", "content": content, "created_at": generated_at})
    news = []
    for item in record.get("news", []) or []:
        if isinstance(item, dict):
            news.append(
                {
                    "title": str(item.get("title", "")),
                    "source": str(item.get("source", "")),
                    "published": str(item.get("published", "")),
                    "link": str(item.get("link", "")),
                }
            )
    context = record.get("beijing_context", {})
    return {
        "date": record_date,
        "generated_at": generated_at,
        "content": content,
        "messages": messages,
        "beijing_context": context if isinstance(context, dict) else {},
        "extra_question": str(record.get("extra_question", "")),
        "news": news,
        "source": str(record.get("source", "local")),
    }


def is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def number(value: Any, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    return default if pd.isna(parsed) else float(parsed)
