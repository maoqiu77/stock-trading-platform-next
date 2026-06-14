import { ArrowDownIcon, ArrowUpIcon, LayoutDashboardIcon } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  formatPercent,
  formatPrice,
  getChangeClass,
} from "@/features/charts/format";
import type { Quote } from "@/features/charts/types";
import { cn } from "@/lib/utils";

export function OverviewPanel({
  quotes,
}: {
  quotes: Quote[];
}) {
  const gainers = quotes.filter((quote) => quote.changePercent > 0).length;
  const decliners = quotes.filter((quote) => quote.changePercent < 0).length;
  const flat = Math.max(quotes.length - gainers - decliners, 0);
  const averageChange = quotes.length
    ? quotes.reduce((total, quote) => total + quote.changePercent, 0) /
      quotes.length
    : undefined;
  const sorted = [...quotes].sort(
    (first, second) => second.changePercent - first.changePercent
  );
  const leader = sorted[0];
  const laggard = sorted[sorted.length - 1];

  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2">
          <LayoutDashboardIcon />
          总览
        </CardTitle>
        <CardDescription>自选池、涨跌分布、领涨领跌</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <OverviewMetric
          label="自选数量"
          value={quotes.length ? `${quotes.length}` : "--"}
          detail={`上涨 ${gainers} · 下跌 ${decliners} · 平盘 ${flat}`}
        />
        <OverviewMetric
          label="平均涨跌"
          value={formatPercent(averageChange)}
          detail="当前 watchlist 等权计算"
          valueClassName={getChangeClass(averageChange)}
        />
        <QuoteMetric
          label="领涨"
          quote={leader}
          icon={<ArrowUpIcon />}
        />
        <QuoteMetric
          label="领跌"
          quote={laggard}
          icon={<ArrowDownIcon />}
        />
      </CardContent>
    </Card>
  );
}

function OverviewMetric({
  label,
  value,
  detail,
  valueClassName,
}: {
  label: string;
  value: string;
  detail: string;
  valueClassName?: string;
}) {
  return (
    <div className="rounded-lg bg-muted/50 p-2.5">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={cn("mt-1 text-xl font-semibold tabular-nums", valueClassName)}>
        {value}
      </div>
      <div className="mt-1 truncate text-xs text-muted-foreground">{detail}</div>
    </div>
  );
}

function QuoteMetric({
  label,
  quote,
  icon,
}: {
  label: string;
  quote?: Quote;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-lg bg-muted/50 p-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs text-muted-foreground">{label}</div>
        {icon}
      </div>
      <div className="mt-2 flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{quote?.ticker ?? "--"}</div>
          <div className="truncate text-xs text-muted-foreground">
            {quote?.name ?? "等待行情"}
          </div>
        </div>
        <div className="text-right">
          <div className="text-sm font-medium tabular-nums">
            {formatPrice(quote?.price)}
          </div>
          <div
            className={cn(
              "text-xs font-medium tabular-nums",
              getChangeClass(quote?.changePercent)
            )}
          >
            {formatPercent(quote?.changePercent)}
          </div>
        </div>
      </div>
    </div>
  );
}
