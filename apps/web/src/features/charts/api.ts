import { TIMEFRAMES, type ChartResponse, type Quote, type TimeframeKey, type WatchlistItem } from "@/features/charts/types";
import { buildQuotesPath } from "@/features/charts/quote-path";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "";

type ApiList<T> = {
  items: T[];
};

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${path}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  const data = await requestJson<ApiList<WatchlistItem>>("/api/watchlist");
  return data.items;
}

export async function fetchQuotes(
  tickers: string[] = [],
  refresh = false
): Promise<Quote[]> {
  const data = await requestJson<ApiList<Quote>>(buildQuotesPath(tickers, refresh));
  return data.items;
}

export async function fetchChart(
  ticker: string,
  timeframeKey: TimeframeKey,
  refresh = false
): Promise<ChartResponse> {
  const timeframe = TIMEFRAMES.find((item) => item.key === timeframeKey) ?? TIMEFRAMES[2];
  const refreshQuery = refresh ? "&refresh=1" : "";
  return requestJson<ChartResponse>(
    `/api/charts/${encodeURIComponent(ticker)}?range=${timeframe.range}&interval=${timeframe.interval}${refreshQuery}`
  );
}
