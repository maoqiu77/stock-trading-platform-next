import { TIMEFRAMES, type ChartResponse, type Quote, type TimeframeKey, type WatchlistItem } from "@/features/charts/types";

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

export async function fetchQuotes(tickers: string[] = []): Promise<Quote[]> {
  const query = tickers.map((ticker) => `ticker=${encodeURIComponent(ticker)}`);
  const suffix = query.length ? `?${query.join("&")}` : "";
  const data = await requestJson<ApiList<Quote>>(`/api/quotes${suffix}`);
  return data.items;
}

export async function fetchChart(
  ticker: string,
  timeframeKey: TimeframeKey
): Promise<ChartResponse> {
  const timeframe = TIMEFRAMES.find((item) => item.key === timeframeKey) ?? TIMEFRAMES[2];
  return requestJson<ChartResponse>(
    `/api/charts/${encodeURIComponent(ticker)}?range=${timeframe.range}&interval=${timeframe.interval}`
  );
}
