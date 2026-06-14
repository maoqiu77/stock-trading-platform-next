import { useQuery } from "@tanstack/react-query";

import { fetchChart, fetchQuotes, fetchWatchlist } from "@/features/charts/api";
import type { TimeframeKey } from "@/features/charts/types";

export function useWatchlistQuery() {
  return useQuery({
    queryKey: ["watchlist"],
    queryFn: fetchWatchlist,
  });
}

export function useQuotesQuery(tickers: string[]) {
  return useQuery({
    queryKey: ["quotes", tickers],
    queryFn: () => fetchQuotes(tickers),
    enabled: tickers.length > 0,
    refetchInterval: 60_000,
  });
}

export function useChartQuery(ticker: string, timeframe: TimeframeKey) {
  return useQuery({
    queryKey: ["chart", ticker, timeframe],
    queryFn: () => fetchChart(ticker, timeframe),
    enabled: Boolean(ticker),
  });
}
