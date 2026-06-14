from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

from app.modules.indicators import add_indicators


@dataclass
class BacktestResult:
    name: str
    metrics: dict[str, Any]
    equity_curve: pd.DataFrame
    trades: pd.DataFrame


@dataclass
class DcaPlan:
    amount: float
    interval_unit: str = "month"
    interval_count: int = 1
    weekday: int = 0
    month_day: int = 1
    month_end: bool = False


def dca_plan_from_params(params: dict[str, Any]) -> DcaPlan:
    interval_count = int(number(params.get("dca_interval_count"), 1))
    weekday = int(number(params.get("dca_weekday"), 0))
    month_day = int(number(params.get("dca_month_day"), 1))
    return DcaPlan(
        amount=max(number(params.get("monthly_dca_amount"), 0.0), 0.0),
        interval_unit=str(params.get("dca_interval_unit", "month")).lower(),
        interval_count=max(interval_count, 1),
        weekday=min(max(weekday, 0), 6),
        month_day=min(max(month_day, 1), 31),
        month_end=bool(params.get("dca_month_end", False)),
    )


def resolved_dca_dates(
    trading_index: pd.DatetimeIndex,
    start: pd.Timestamp,
    end: pd.Timestamp,
    params: dict[str, Any],
) -> list[pd.Timestamp]:
    if len(trading_index) == 0:
        return []
    plan = dca_plan_from_params(params)
    index = pd.DatetimeIndex(pd.to_datetime(trading_index)).sort_values().normalize()
    end = pd.Timestamp(end).normalize()
    resolved: list[pd.Timestamp] = []
    for scheduled in _scheduled_dca_dates(pd.Timestamp(start), end, plan):
        pos = index.searchsorted(scheduled)
        if pos >= len(index):
            continue
        trading_day = index[pos]
        if trading_day <= end:
            resolved.append(pd.Timestamp(trading_day))
    return resolved


def buy_and_hold(df: pd.DataFrame, initial_cash: float) -> BacktestResult:
    if df.empty:
        return empty_result("Buy and Hold")
    price0 = float(df["Close"].iloc[0])
    shares = initial_cash / price0 if price0 > 0 else 0.0
    equity = df["Close"] * shares
    trades = [
        {
            "Date": df.index[0],
            "Action": "BUY",
            "Price": price0,
            "Shares": shares,
            "Amount": initial_cash,
            "Reason": "初始资金一次性买入并持有",
        }
    ]
    return BacktestResult(
        "Buy and Hold",
        metrics(equity, trades, initial_cash),
        pd.DataFrame({"Equity": equity}),
        pd.DataFrame(trades),
    )


def lump_sum_buy_and_hold(
    df: pd.DataFrame,
    initial_cash: float,
    contributions: dict[pd.Timestamp, float],
) -> BacktestResult:
    if df.empty:
        return empty_result("Lump Sum Buy and Hold")
    total_principal = initial_cash + sum(contributions.values())
    price0 = float(df["Close"].iloc[0])
    shares = total_principal / price0 if price0 > 0 else 0.0
    equity = df["Close"] * shares
    trades = [
        {
            "Date": df.index[0],
            "Action": "BUY",
            "Price": price0,
            "Shares": shares,
            "Amount": total_principal,
            "Reason": "初始资金和未来计划投入在期初一次性买入",
        }
    ]
    return BacktestResult(
        "Lump Sum Buy and Hold",
        metrics(equity, trades, total_principal),
        pd.DataFrame({"Equity": equity}),
        pd.DataFrame(trades),
    )


def cashflow_buy_and_hold(
    df: pd.DataFrame,
    initial_cash: float,
    contributions: dict[pd.Timestamp, float],
) -> BacktestResult:
    if df.empty:
        return empty_result("Same Cashflow Buy and Hold")
    cash = initial_cash
    shares = 0.0
    trades: list[dict[str, Any]] = []
    equity_values = []
    for dt, row in df.iterrows():
        price = float(row["Close"])
        cash, contribution = add_contribution(cash, contributions, dt)
        cash, bought, amount = buy(cash, price, cash)
        shares += bought
        if amount > 0:
            reason = "初始资金买入" if contribution <= 0 and len(trades) == 0 else "同现金流计划买入"
            trades.append(
                {
                    "Date": dt,
                    "Action": "BUY",
                    "Price": price,
                    "Shares": bought,
                    "Amount": amount,
                    "Reason": reason,
                }
            )
        equity_values.append(cash + shares * price)
    equity = pd.Series(equity_values, index=df.index)
    return BacktestResult(
        "Same Cashflow Buy and Hold",
        metrics(equity, trades, initial_cash + sum(contributions.values())),
        pd.DataFrame({"Equity": equity}),
        pd.DataFrame(trades),
    )


def monthly_dca(
    df: pd.DataFrame,
    initial_cash: float,
    monthly_amount: float,
) -> BacktestResult:
    if df.empty:
        return empty_result("Monthly DCA")
    cash = initial_cash
    shares = 0.0
    trades: list[dict[str, Any]] = []
    equity_values = []
    last_month = None
    for dt, row in df.iterrows():
        month = (dt.year, dt.month)
        price = float(row["Close"])
        if month != last_month and cash > 0:
            cash, bought, amount = buy(cash, price, monthly_amount)
            shares += bought
            if amount > 0:
                trades.append(
                    {
                        "Date": dt,
                        "Action": "BUY",
                        "Price": price,
                        "Shares": bought,
                        "Amount": amount,
                        "Reason": "每月第一个交易日定投",
                    }
                )
            last_month = month
        equity_values.append(cash + shares * price)
    equity = pd.Series(equity_values, index=df.index)
    return BacktestResult(
        "Monthly DCA",
        metrics(equity, trades, initial_cash),
        pd.DataFrame({"Equity": equity}),
        pd.DataFrame(trades),
    )


def ma200_filter(
    df: pd.DataFrame,
    initial_cash: float,
    monthly_amount: float,
    sell_on_break: bool,
    ma_window: int = 200,
) -> BacktestResult:
    if df.empty:
        return empty_result("MA200 Risk Filter")
    data = df.copy()
    data["MA200X"] = data["Close"].rolling(ma_window, min_periods=ma_window).mean()
    cash = initial_cash
    shares = 0.0
    trades: list[dict[str, Any]] = []
    equity_values = []
    last_month = None
    holding_allowed = False
    for dt, row in data.iterrows():
        price = float(row["Close"])
        ma = row["MA200X"]
        above_ma = bool(pd.notna(ma) and price > ma)
        if above_ma:
            holding_allowed = True
        if sell_on_break and holding_allowed and pd.notna(ma) and price < ma and shares > 0:
            amount = shares * price
            cash += amount
            trades.append(
                {
                    "Date": dt,
                    "Action": "SELL",
                    "Price": price,
                    "Shares": shares,
                    "Amount": amount,
                    "Reason": "跌破 MA200，卖出转现金",
                }
            )
            shares = 0.0
            holding_allowed = False
        month = (dt.year, dt.month)
        if month != last_month and above_ma and cash > 0:
            cash, bought, amount = buy(cash, price, monthly_amount)
            shares += bought
            if amount > 0:
                trades.append(
                    {
                        "Date": dt,
                        "Action": "BUY",
                        "Price": price,
                        "Shares": bought,
                        "Amount": amount,
                        "Reason": "收盘价高于 MA200，允许新增买入",
                    }
                )
            last_month = month
        elif month != last_month:
            last_month = month
        equity_values.append(cash + shares * price)
    name = "MA200 Risk Filter - Sell to Cash" if sell_on_break else "MA200 Risk Filter - Hold Cash"
    equity = pd.Series(equity_values, index=df.index)
    return BacktestResult(
        name,
        metrics(equity, trades, initial_cash),
        pd.DataFrame({"Equity": equity}),
        pd.DataFrame(trades),
    )


def cashflow_ma_filter(
    df: pd.DataFrame,
    initial_cash: float,
    contributions: dict[pd.Timestamp, float],
    sell_on_break: bool,
    ma_window: int = 200,
) -> BacktestResult:
    if df.empty:
        return empty_result("MA200 Risk Filter")
    data = df.copy()
    data["MA200X"] = data["Close"].rolling(ma_window, min_periods=ma_window).mean()
    cash = initial_cash
    shares = 0.0
    trades: list[dict[str, Any]] = []
    equity_values = []
    holding_allowed = False
    for dt, row in data.iterrows():
        price = float(row["Close"])
        cash, contribution = add_contribution(cash, contributions, dt)
        ma = row["MA200X"]
        above_ma = bool(pd.notna(ma) and price > ma)
        if above_ma:
            holding_allowed = True
        if sell_on_break and holding_allowed and pd.notna(ma) and price < ma and shares > 0:
            amount = shares * price
            cash += amount
            trades.append(
                {
                    "Date": dt,
                    "Action": "SELL",
                    "Price": price,
                    "Shares": shares,
                    "Amount": amount,
                    "Reason": "跌破 MA，卖出转现金",
                }
            )
            shares = 0.0
            holding_allowed = False
        if above_ma and cash > 0:
            cash, bought, amount = buy(cash, price, cash)
            shares += bought
            if amount > 0:
                reason = "收盘价高于 MA，允许买入"
                if contribution > 0:
                    reason = "定投现金流到账且收盘价高于 MA，允许买入"
                trades.append(
                    {
                        "Date": dt,
                        "Action": "BUY",
                        "Price": price,
                        "Shares": bought,
                        "Amount": amount,
                        "Reason": reason,
                    }
                )
        equity_values.append(cash + shares * price)
    name = "MA200 Risk Filter - Sell to Cash" if sell_on_break else "MA200 Risk Filter - Hold Cash"
    equity = pd.Series(equity_values, index=df.index)
    return BacktestResult(
        name,
        metrics(equity, trades, initial_cash + sum(contributions.values())),
        pd.DataFrame({"Equity": equity}),
        pd.DataFrame(trades),
    )


def trend_pullback_add(
    df: pd.DataFrame,
    initial_cash: float,
    params: dict[str, Any],
    contributions: dict[pd.Timestamp, float] | None = None,
) -> BacktestResult:
    if df.empty:
        return empty_result("Trend Pullback Add")
    data = add_indicators(df, int(params.get("rsi_period", 14)))
    ma_medium = int(params.get("ma_medium", 60))
    ma_long = int(params.get("ma_long", 120))
    data["MAMedium"] = data["Close"].rolling(ma_medium, min_periods=ma_medium).mean()
    data["MALong"] = data["Close"].rolling(ma_long, min_periods=ma_long).mean()
    cash = initial_cash
    shares = 0.0
    trades: list[dict[str, Any]] = []
    equity_values = []
    target_weight = float(params.get("target_weight_default", 1.0))
    max_asset_ratio = float(params.get("single_add_asset_ratio", 0.05))
    max_cash_ratio = float(params.get("single_add_cash_ratio", 0.20))
    pullback_min = float(params.get("pullback_min", 0.03))
    pullback_max = float(params.get("pullback_max", 0.08))
    rsi_max = float(params.get("rsi_max", 75))
    for dt, row in data.iterrows():
        price = float(row["Close"])
        cash, _ = add_contribution(cash, contributions or {}, dt)
        equity_now = cash + shares * price
        current_value = shares * price
        target_gap = max(equity_now * target_weight - current_value, 0)
        can_buy = (
            pd.notna(row["MAMedium"])
            and pd.notna(row["MALong"])
            and price > row["MAMedium"]
            and price > row["MALong"]
            and pullback_min <= row["Drawdown20"] <= pullback_max
            and row["RSI14"] <= rsi_max
            and target_gap > 0
            and cash > 0
        )
        if can_buy:
            amount = min(target_gap, equity_now * max_asset_ratio, cash * max_cash_ratio, cash)
            cash, bought, actual = buy(cash, price, amount)
            shares += bought
            if actual > 0:
                trades.append(
                    {
                        "Date": dt,
                        "Action": "BUY",
                        "Price": price,
                        "Shares": bought,
                        "Amount": actual,
                        "Reason": "趋势未破坏且 20 日高点回撤处于区间",
                    }
                )
        equity_values.append(cash + shares * price)
    equity = pd.Series(equity_values, index=df.index)
    return BacktestResult(
        "Trend Pullback Add",
        metrics(equity, trades, initial_cash + sum((contributions or {}).values())),
        pd.DataFrame({"Equity": equity}),
        pd.DataFrame(trades),
    )


def layered_pullback_add(
    df: pd.DataFrame,
    initial_cash: float,
    params: dict[str, Any],
    contributions: dict[pd.Timestamp, float] | None = None,
) -> BacktestResult:
    if df.empty:
        return empty_result("Layered Pullback Add")
    data = add_indicators(df, int(params.get("rsi_period", 14)))
    ma_long = int(params.get("ma_long", 120))
    data["MALong"] = data["Close"].rolling(ma_long, min_periods=ma_long).mean()
    cash = initial_cash
    shares = 0.0
    trades: list[dict[str, Any]] = []
    equity_values = []
    plan_amount = float(params.get("layered_plan_amount", initial_cash * 0.10))
    layers = params.get(
        "layered_pullbacks",
        [
            {"min": 0.03, "max": 0.08, "ratio": 0.25},
            {"min": 0.08, "max": 0.15, "ratio": 0.35},
            {"min": 0.15, "max": 0.25, "ratio": 0.40},
        ],
    )
    for dt, row in data.iterrows():
        price = float(row["Close"])
        cash, _ = add_contribution(cash, contributions or {}, dt)
        amount = 0.0
        reason = ""
        if pd.notna(row["MALong"]) and price > row["MALong"]:
            for layer in layers:
                if float(layer["min"]) <= row["Drawdown20"] < float(layer["max"]):
                    amount = plan_amount * float(layer["ratio"])
                    reason = f"分层回撤 {float(layer['min']):.0%}-{float(layer['max']):.0%}，使用计划资金 {float(layer['ratio']):.0%}"
                    break
        if amount > 0 and cash > 0:
            cash, bought, actual = buy(cash, price, amount)
            shares += bought
            if actual > 0:
                trades.append(
                    {
                        "Date": dt,
                        "Action": "BUY",
                        "Price": price,
                        "Shares": bought,
                        "Amount": actual,
                        "Reason": reason,
                    }
                )
        equity_values.append(cash + shares * price)
    equity = pd.Series(equity_values, index=df.index)
    return BacktestResult(
        "Layered Pullback Add",
        metrics(equity, trades, initial_cash + sum((contributions or {}).values())),
        pd.DataFrame({"Equity": equity}),
        pd.DataFrame(trades),
    )


def run_strategy_comparison(
    df: pd.DataFrame,
    initial_cash: float,
    params: dict[str, Any],
) -> list[BacktestResult]:
    clean = df.dropna(subset=["Close"]).copy()
    if clean.empty:
        return []
    contributions = contributions_by_date(clean, params)
    lump_sum_benchmark = lump_sum_buy_and_hold(clean, initial_cash, contributions)
    cashflow_benchmark = cashflow_buy_and_hold(clean, initial_cash, contributions)
    results = [
        lump_sum_benchmark,
        cashflow_benchmark,
        cashflow_ma_filter(clean, initial_cash, contributions, sell_on_break=False, ma_window=int(params.get("ma_risk", 200))),
        cashflow_ma_filter(clean, initial_cash, contributions, sell_on_break=True, ma_window=int(params.get("ma_risk", 200))),
        trend_pullback_add(clean, initial_cash, params, contributions),
        layered_pullback_add(clean, initial_cash, params, contributions),
    ]
    cashflow_return = cashflow_benchmark.metrics.get("总收益率", 0)
    lump_sum_return = lump_sum_benchmark.metrics.get("总收益率", 0)
    for result in results:
        result.metrics["相对同现金流买入持有差异"] = result.metrics.get("总收益率", 0) - cashflow_return
        result.metrics["相对期初一次性买入持有差异"] = result.metrics.get("总收益率", 0) - lump_sum_return
        result.metrics["相对买入持有差异"] = result.metrics["相对同现金流买入持有差异"]
    return results


def run_legacy_strategy_set(
    df: pd.DataFrame,
    initial_cash: float,
    params: dict[str, Any],
) -> list[BacktestResult]:
    clean = df.dropna(subset=["Close"]).copy()
    if clean.empty:
        return []
    monthly_amount = max(number(params.get("monthly_dca_amount"), 0.0), 0.0)
    ma_window = int(number(params.get("ma_risk"), 200))
    return [
        buy_and_hold(clean, initial_cash),
        monthly_dca(clean, initial_cash, monthly_amount),
        ma200_filter(clean, initial_cash, monthly_amount, sell_on_break=False, ma_window=ma_window),
        ma200_filter(clean, initial_cash, monthly_amount, sell_on_break=True, ma_window=ma_window),
    ]


def result_to_dict(result: BacktestResult) -> dict[str, Any]:
    trades = result.trades.copy()
    if "Date" in trades.columns:
        trades["Date"] = trades["Date"].astype(str)
    equity = result.equity_curve.copy()
    equity_rows = [
        {"date": str(index.date() if hasattr(index, "date") else index), "equity": float(row["Equity"])}
        for index, row in equity.tail(240).iterrows()
    ]
    return {
        "name": result.name,
        "metrics": clean_json(result.metrics),
        "equity": equity_rows,
        "trades": clean_json(trades.tail(50).to_dict("records")),
    }


def empty_result(name: str) -> BacktestResult:
    return BacktestResult(
        name,
        {},
        pd.DataFrame(columns=["Equity"]),
        pd.DataFrame(columns=["Date", "Action", "Price", "Shares", "Amount", "Reason"]),
    )


def contributions_by_date(df: pd.DataFrame, params: dict[str, Any]) -> dict[pd.Timestamp, float]:
    plan = dca_plan_from_params(params)
    if df.empty or plan.amount <= 0:
        return {}
    start = pd.Timestamp(df.index[0])
    end = pd.Timestamp(df.index[-1])
    contributions: dict[pd.Timestamp, float] = {}
    for dt in resolved_dca_dates(pd.DatetimeIndex(df.index), start, end, params):
        contributions[dt] = contributions.get(dt, 0.0) + plan.amount
    return contributions


def metrics(
    equity: pd.Series,
    trades: list[dict[str, Any]],
    invested_principal: float,
    cashflow_benchmark_return: float | None = None,
    lump_sum_benchmark_return: float | None = None,
) -> dict[str, Any]:
    if equity.empty:
        return {}
    final_assets = float(equity.iloc[-1])
    invested_principal = float(max(invested_principal, 0.0))
    pnl = final_assets - invested_principal
    total_return = pnl / invested_principal if invested_principal > 0 else 0.0
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1 / 365.25)
    cagr = (final_assets / invested_principal) ** (1 / years) - 1 if invested_principal > 0 and final_assets > 0 else 0.0
    daily_returns = equity.pct_change().dropna()
    sharpe = 0.0
    if daily_returns.std() != 0 and not daily_returns.empty:
        sharpe = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252))
    drawdown = equity / equity.cummax() - 1
    trade_df = pd.DataFrame(trades)
    sells = trade_df[trade_df["Action"].eq("SELL")] if not trade_df.empty else pd.DataFrame()
    wins = int((sells["Amount"] > 0).sum()) if not sells.empty else 0
    return {
        "累计投入本金": invested_principal,
        "最终资产": final_assets,
        "总盈亏": pnl,
        "资金收益率": total_return,
        "总收益率": total_return,
        "CAGR": cagr,
        "最大回撤": float(drawdown.min()),
        "夏普比率": sharpe,
        "交易次数": int(len(trade_df)),
        "胜率": (wins / len(sells)) if len(sells) else 0.0,
        "相对同现金流买入持有差异": total_return - cashflow_benchmark_return if cashflow_benchmark_return is not None else 0.0,
        "相对期初一次性买入持有差异": total_return - lump_sum_benchmark_return if lump_sum_benchmark_return is not None else 0.0,
        "相对买入持有差异": total_return - cashflow_benchmark_return if cashflow_benchmark_return is not None else 0.0,
    }


def month_date(year: int, month: int, plan: DcaPlan) -> pd.Timestamp:
    last_day = calendar.monthrange(year, month)[1]
    day = last_day if plan.month_end else min(plan.month_day, last_day)
    return pd.Timestamp(year=year, month=month, day=day)


def scheduled_dca_dates(start: pd.Timestamp, end: pd.Timestamp, plan: DcaPlan) -> list[pd.Timestamp]:
    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()
    dates: list[pd.Timestamp] = []
    if plan.interval_unit == "day":
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=plan.interval_count)
        return dates
    if plan.interval_unit == "week":
        days_until = (plan.weekday - start.weekday()) % 7
        current = start + timedelta(days=days_until)
        while current <= end:
            dates.append(current)
            current += timedelta(weeks=plan.interval_count)
        return dates

    current = month_date(start.year, start.month, plan)
    if current < start:
        next_month = start + pd.DateOffset(months=1)
        current = month_date(next_month.year, next_month.month, plan)
    while current <= end:
        dates.append(current)
        next_month = current + pd.DateOffset(months=plan.interval_count)
        current = month_date(next_month.year, next_month.month, plan)
    return dates


def add_contribution(
    cash: float,
    contributions: dict[pd.Timestamp, float],
    dt: pd.Timestamp,
) -> tuple[float, float]:
    amount = float(contributions.get(pd.Timestamp(dt).normalize(), 0.0))
    return cash + amount, amount


def buy(cash: float, price: float, amount: float) -> tuple[float, float, float]:
    actual = min(max(amount, 0), cash)
    shares = actual / price if price > 0 else 0
    return cash - actual, shares, actual


def number(value: Any, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    return default if pd.isna(parsed) else float(parsed)


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    return value


_scheduled_dca_dates = scheduled_dca_dates
