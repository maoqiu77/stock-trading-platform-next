from __future__ import annotations

import unittest

from app.modules.trading_data import derive_positions


class TradingDataTest(unittest.TestCase):
    def test_derive_positions_removes_sold_shares_from_oldest_lots_first(self) -> None:
        [position] = derive_positions(
            {
                "stockPool": ["VOO"],
                "positions": [
                    {
                        "ticker": "VOO",
                        "targetWeight": 0.2,
                        "assetType": "ETF",
                        "takeProfitPct": 0.0,
                        "stopLossPct": 0.0,
                        "purchaseDate": "",
                    }
                ],
                "trades": [
                    {
                        "date": "2026-06-01",
                        "ticker": "VOO",
                        "action": "买入",
                        "shares": 10,
                        "unitPrice": 10,
                        "amount": 100,
                    },
                    {
                        "date": "2026-06-02",
                        "ticker": "VOO",
                        "action": "买入",
                        "shares": 10,
                        "unitPrice": 20,
                        "amount": 200,
                    },
                    {
                        "date": "2026-06-03",
                        "ticker": "VOO",
                        "action": "卖出",
                        "shares": 10,
                        "unitPrice": 15,
                        "amount": 150,
                    },
                ],
            }
        )

        self.assertEqual(position["shares"], 10)
        self.assertEqual(position["costBasis"], 20)
        self.assertEqual(position["holdingCost"], 200)


if __name__ == "__main__":
    unittest.main()
