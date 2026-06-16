import * as React from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchChart, fetchQuotes, fetchWatchlist } from "@/features/charts/api";
import type { TimeframeKey } from "@/features/charts/types";

export function useWatchlistQuery() {
  return useQuery({
    queryKey: ["watchlist"],
    queryFn: fetchWatchlist,
  });
}

export function useQuotesQuery(tickers: string[], refreshKey = 0) {
  const consumedRefreshKeyRef = React.useRef(refreshKey);
  return useQuery({
    queryKey: ["quotes", tickers, refreshKey],
    queryFn: () => {
      const shouldRefresh = refreshKey !== consumedRefreshKeyRef.current;
      consumedRefreshKeyRef.current = refreshKey;
      return tickers.length
        ? fetchQuotes(tickers, shouldRefresh)
        : Promise.resolve([]);
    },
    refetchInterval: tickers.length ? 15_000 : false,
  });
}

export function useChartQuery(
  ticker: string,
  timeframe: TimeframeKey,
  refreshKey = 0
) {
  const consumedRefreshKeyRef = React.useRef(refreshKey);
  return useQuery({
    queryKey: ["chart", ticker, timeframe, refreshKey],
    queryFn: () => {
      const shouldRefresh = refreshKey !== consumedRefreshKeyRef.current;
      consumedRefreshKeyRef.current = refreshKey;
      return fetchChart(ticker, timeframe, shouldRefresh);
    },
    enabled: Boolean(ticker),
  });
}
