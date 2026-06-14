from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PositionContext:
    market_value: float
    current_weight: float
    target_value: float
    gap_to_target: float


def calculate_position_context(
    price: float,
    shares: float,
    total_assets: float,
    target_weight: float,
) -> PositionContext:
    market_value = max(price, 0) * max(shares, 0)
    current_weight = market_value / total_assets if total_assets > 0 else 0
    target_value = total_assets * max(target_weight, 0)
    gap = max(target_value - market_value, 0)
    return PositionContext(market_value, current_weight, target_value, gap)


def suggested_add_amount(
    gap_to_target: float,
    total_assets: float,
    cash: float,
    max_asset_ratio: float,
    max_cash_ratio: float,
) -> float:
    if gap_to_target <= 0 or cash <= 0 or total_assets <= 0:
        return 0.0
    return max(
        0.0,
        min(gap_to_target, total_assets * max_asset_ratio, cash * max_cash_ratio, cash),
    )
