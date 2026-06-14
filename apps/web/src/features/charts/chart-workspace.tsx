"use client";

import { AlertCircleIcon } from "lucide-react";
import * as React from "react";

import {
  Alert,
  AlertAction,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { InsightPanel } from "@/features/charts/insight-panel";
import { MarketChart } from "@/features/charts/market-chart";
import {
  useChartQuery,
  useQuotesQuery,
  useWatchlistQuery,
} from "@/features/charts/queries";
import { SymbolHeader } from "@/features/charts/symbol-header";
import { TimeframeTabs } from "@/features/charts/timeframe-tabs";
import { TIMEFRAMES, type TimeframeKey } from "@/features/charts/types";
import { WatchlistRail } from "@/features/charts/watchlist-rail";
import { useTradingData } from "@/features/platform/trading-data-context";

export function ChartWorkspace() {
  const [selectedTicker, setSelectedTicker] = React.useState("VOO");
  const [timeframeKey, setTimeframeKey] = React.useState<TimeframeKey>("D");
  const { state } = useTradingData();

  const watchlistQuery = useWatchlistQuery();
  const tickers = React.useMemo(
    () => watchlistQuery.data?.map((item) => item.ticker) ?? [],
    [watchlistQuery.data]
  );
  const activeTicker = tickers.includes(selectedTicker)
    ? selectedTicker
    : tickers[0] ?? selectedTicker;
  const quotesQuery = useQuotesQuery(tickers);
  const chartQuery = useChartQuery(activeTicker, timeframeKey);

  const timeframe =
    TIMEFRAMES.find((item) => item.key === timeframeKey) ?? TIMEFRAMES[2];
  const quotes = quotesQuery.data ?? [];
  const selectedQuote = quotes.find((item) => item.ticker === activeTicker);
  const selectedTrades = React.useMemo(
    () => state.trades.filter((trade) => trade.ticker === activeTicker),
    [activeTicker, state.trades]
  );
  const hasDataError =
    watchlistQuery.isError || quotesQuery.isError || chartQuery.isError;

  return (
    <div className="grid min-h-[calc(100svh-6.5rem)] gap-3 xl:grid-cols-[232px_minmax(0,1fr)]">
      <aside className="min-h-0 xl:sticky xl:top-3 xl:self-start">
        <WatchlistRail
          quotes={quotes}
          selectedTicker={activeTicker}
          isLoading={watchlistQuery.isLoading || quotesQuery.isLoading}
          onSelect={setSelectedTicker}
        />
      </aside>
      <section className="flex min-w-0 flex-col gap-3">
        <Card className="flex min-h-[640px] flex-col xl:h-[calc(100svh-6.5rem)]">
          <CardHeader className="border-b">
            <div className="flex flex-col gap-4">
              <SymbolHeader
                ticker={activeTicker}
                quote={selectedQuote}
                timeframe={timeframe}
              />
              <TimeframeTabs value={timeframeKey} onChange={setTimeframeKey} />
            </div>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col px-0 pb-0">
            {hasDataError ? (
              <Alert variant="destructive" className="m-3">
                <AlertCircleIcon />
                <AlertTitle>行情接口暂不可用</AlertTitle>
                <AlertDescription>
                  请确认 FastAPI 已启动；后端本身会在行情源失败时返回样例数据。
                </AlertDescription>
                <AlertAction>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      void watchlistQuery.refetch();
                      void quotesQuery.refetch();
                      void chartQuery.refetch();
                    }}
                  >
                    重试
                  </Button>
                </AlertAction>
              </Alert>
            ) : chartQuery.isLoading || !chartQuery.data ? (
              <ChartLoading />
            ) : (
              <MarketChart data={chartQuery.data} trades={selectedTrades} />
            )}
          </CardContent>
          <CardFooter className="justify-between gap-3 text-xs text-muted-foreground">
            <span>{timeframe.description}</span>
            <span className="truncate">
              {chartQuery.data?.lastUpdated
                ? `Updated ${new Date(chartQuery.data.lastUpdated).toLocaleString("zh-CN")}`
                : "等待数据"}
            </span>
          </CardFooter>
        </Card>
        <InsightPanel chart={chartQuery.data} timeframe={timeframe} />
      </section>
    </div>
  );
}

function ChartLoading() {
  return (
    <div className="flex flex-1 flex-col gap-3 p-3">
      <Skeleton className="h-6 w-40" />
      <Skeleton className="min-h-[420px] flex-1 w-full" />
      <div className="grid grid-cols-4 gap-3">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    </div>
  );
}
