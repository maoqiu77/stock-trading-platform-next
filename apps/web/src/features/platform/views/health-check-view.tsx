"use client";

import {
  ActivityIcon,
  BotIcon,
  ShieldCheckIcon,
  WifiIcon,
} from "lucide-react";

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
import { useQuotesQuery, useWatchlistQuery } from "@/features/charts/queries";
import { useAiSettingsQuery } from "@/features/platform/queries";
import { useTradingData } from "@/features/platform/trading-data-context";

export function HealthCheckView() {
  const { state, storageStatus, validationIssues } = useTradingData();
  const watchlistQuery = useWatchlistQuery();
  const aiSettingsQuery = useAiSettingsQuery();
  const quotesQuery = useQuotesQuery(state.stockPool);
  const quotes = quotesQuery.data ?? [];
  const sourceSummary = summarizeQuoteSources(quotes.map((quote) => quote.source));
  const apiOnline = storageStatus === "api" || storageStatus === "saving";
  const aiReady =
    Boolean(aiSettingsQuery.data?.baseUrl) &&
    Boolean(aiSettingsQuery.data?.model) &&
    Boolean(aiSettingsQuery.data?.hasApiKey);

  return (
    <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="grid gap-3">
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <ActivityIcon />
              运行状态
            </CardTitle>
            <CardDescription>启动后先看这里，判断服务和本地数据是否正常</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableBody>
                <HealthRow
                  label="本地 API / SQLite"
                  value={apiOnline ? "在线" : statusLabel(storageStatus)}
                  status={apiOnline ? "ok" : "warn"}
                />
                <HealthRow
                  label="自选池"
                  value={`${state.stockPool.length} 个标的`}
                  status={state.stockPool.length ? "ok" : "warn"}
                />
                <HealthRow
                  label="接口自选列表"
                  value={
                    watchlistQuery.isError
                      ? "读取失败"
                      : `${watchlistQuery.data?.length ?? 0} 个标的`
                  }
                  status={watchlistQuery.isError ? "warn" : "ok"}
                />
                <HealthRow
                  label="校验问题"
                  value={
                    validationIssues.length
                      ? `${validationIssues.length} 项需要处理`
                      : "未发现"
                  }
                  status={validationIssues.length ? "warn" : "ok"}
                />
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <WifiIcon />
              行情可信度
            </CardTitle>
            <CardDescription>区分真实行情、延迟行情和样例数据</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableBody>
                <HealthRow
                  label="行情请求"
                  value={
                    quotesQuery.isError
                      ? "读取失败"
                      : quotesQuery.isLoading
                        ? "读取中"
                        : "可用"
                  }
                  status={quotesQuery.isError ? "warn" : "ok"}
                />
                <HealthRow
                  label="来源分布"
                  value={sourceSummary || "暂无报价"}
                  status={quotes.some((quote) => quote.source === "sample") ? "warn" : "ok"}
                />
                <HealthRow
                  label="样例数据"
                  value={
                    quotes.some((quote) => quote.source === "sample")
                      ? "部分标的使用 sample，不应用作真实交易依据"
                      : "当前报价未标记为 sample"
                  }
                  status={quotes.some((quote) => quote.source === "sample") ? "warn" : "ok"}
                />
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-3 self-start">
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <BotIcon />
              AI 接口
            </CardTitle>
            <CardDescription>OpenAI-compatible chat/completions 配置</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableBody>
                <HealthRow
                  label="配置状态"
                  value={aiReady ? "已配置" : "未配置完整"}
                  status={aiReady ? "ok" : "warn"}
                />
                <HealthRow
                  label="Base URL"
                  value={aiSettingsQuery.data?.baseUrl || "未设置"}
                  status={aiSettingsQuery.data?.baseUrl ? "ok" : "warn"}
                />
                <HealthRow
                  label="模型"
                  value={aiSettingsQuery.data?.model || "未设置"}
                  status={aiSettingsQuery.data?.model ? "ok" : "warn"}
                />
                <HealthRow
                  label="密钥"
                  value={aiSettingsQuery.data?.hasApiKey ? "已保存本地密钥" : "未保存"}
                  status={aiSettingsQuery.data?.hasApiKey ? "ok" : "warn"}
                />
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <ShieldCheckIcon />
              本地隐私边界
            </CardTitle>
            <CardDescription>给他人使用时最重要的检查点</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableBody>
                <HealthRow label="私有数据" value="storage/local/app.db" status="ok" />
                <HealthRow label="公开模板" value="storage/templates" status="ok" />
                <HealthRow label="AI 发送前确认" value="已启用" status="ok" />
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function HealthRow({
  label,
  value,
  status,
}: {
  label: string;
  value: string;
  status: "ok" | "warn";
}) {
  return (
    <TableRow>
      <TableCell className="text-muted-foreground">{label}</TableCell>
      <TableCell className="text-right">
        <div className="flex justify-end">
          <Badge variant={status === "ok" ? "secondary" : "outline"}>{value}</Badge>
        </div>
      </TableCell>
    </TableRow>
  );
}

function summarizeQuoteSources(sources: string[]) {
  const counts = new Map<string, number>();
  for (const source of sources) {
    counts.set(source, (counts.get(source) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([source, count]) => `${source}: ${count}`)
    .join(" / ");
}

function statusLabel(status: string) {
  if (status === "loading") {
    return "读取中";
  }
  if (status === "local") {
    return "本地兜底";
  }
  if (status === "error") {
    return "保存异常";
  }
  return status;
}
