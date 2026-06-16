export function buildQuotesPath(tickers: string[] = [], refresh = false) {
  const query = tickers.map((ticker) => `ticker=${encodeURIComponent(ticker)}`);
  if (refresh) {
    query.push("refresh=1");
  }
  const suffix = query.length ? `?${query.join("&")}` : "";
  return `/api/quotes${suffix}`;
}
