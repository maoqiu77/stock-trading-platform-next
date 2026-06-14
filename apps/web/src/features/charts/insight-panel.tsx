import { DatabaseIcon, GaugeIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from "@/components/ui/table";
import {
  formatPercent,
  formatPrice,
  formatVolume,
  getChangeClass,
} from "@/features/charts/format";
import type { ChartResponse, TimeframeConfig } from "@/features/charts/types";
import { summarizeBars } from "@/features/charts/format";
import { cn } from "@/lib/utils";

export function InsightPanel({
  chart,
  timeframe,
}: {
  chart?: ChartResponse;
  timeframe: TimeframeConfig;
}) {
  const summary = chart ? summarizeBars(chart.bars) : null;
  const isIntraday = chart
    ? !["1d", "1wk", "1mo"].includes(chart.interval)
    : false;
  const sourceDescription =
    chart?.source === "unavailable"
      ? (chart.message ?? "真实行情暂不可用")
      : chart?.source === "sample"
      ? "当前为样例行情，非最新实时报价"
      : chart?.source
        ? `当前图表来自 ${chart.source}`
        : "等待行情数据";

  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.6fr)]">
      <Card>
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2">
            <GaugeIcon />
            区间统计
          </CardTitle>
          <CardDescription>{timeframe.description}</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table className="min-w-[720px]">
            <TableBody>
              <TableRow>
                <MetricCell label="开盘" value={formatPrice(summary?.open)} />
                <MetricCell label="收盘" value={formatPrice(summary?.close)} />
                <MetricCell label="最高" value={formatPrice(summary?.high)} />
                <MetricCell label="最低" value={formatPrice(summary?.low)} />
                <MetricCell
                  label="涨跌"
                  value={formatPercent(summary?.changePercent)}
                  valueClassName={getChangeClass(summary?.changePercent)}
                />
                <MetricCell label="成交量" value={formatVolume(summary?.volume)} />
                <MetricCell label="样本数" value={summary ? `${summary.count}` : "--"} />
                <MetricCell
                  label="起点"
                  value={timeLabel(summary?.startTime, chart?.timezone, isIntraday)}
                />
                <MetricCell
                  label="最新"
                  value={timeLabel(summary?.endTime, chart?.timezone, isIntraday)}
                />
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2">
            <DatabaseIcon />
            数据状态
          </CardTitle>
          <CardDescription>{sourceDescription}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm">
          <div className="flex items-center justify-between gap-3 rounded-lg bg-muted/50 p-3">
            <span className="text-sm text-muted-foreground">行情源</span>
            <Badge variant="secondary">{chart?.source ?? "loading"}</Badge>
          </div>
          <div className="flex items-center justify-between gap-3 rounded-lg bg-muted/50 p-3">
            <span className="text-sm text-muted-foreground">图表类型</span>
            <Badge variant="outline">
              {chart?.seriesType === "line" ? "分时线" : "蜡烛K线"}
            </Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function timeLabel(value?: string, timezone = "UTC", isIntraday = false) {
  if (!value) {
    return "--";
  }
  if (!value.includes("T")) {
    return value;
  }
  if (!isIntraday) {
    return value.slice(0, 16).replace("T", " ");
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value.slice(0, 16).replace("T", " ");
  }

  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function MetricCell({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <TableCell>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={cn("mt-1 font-medium tabular-nums", valueClassName)}>
        {value}
      </div>
    </TableCell>
  );
}
