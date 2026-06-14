"use client";

import {
  DatabaseIcon,
  ShieldIcon,
} from "lucide-react";

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
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
import { useTradingData } from "@/features/platform/trading-data-context";

export function SettingsView() {
  const { validationIssues, storageStatus } = useTradingData();

  return (
    <div className="flex flex-col gap-3">
      {validationIssues.length ? (
        <Alert variant="destructive">
          <ShieldIcon />
          <AlertTitle>设置需要修正</AlertTitle>
          <AlertDescription>
            {validationIssues.slice(0, 3).join(" ")}
            {validationIssues.length > 3 ? " ..." : ""}
          </AlertDescription>
        </Alert>
      ) : null}
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <DatabaseIcon />
              数据边界
            </CardTitle>
            <CardDescription>本地私有状态保存在 SQLite，提交时排除</CardDescription>
            <Badge variant={storageStatus === "error" ? "outline" : "secondary"}>
              {storageStatusLabel(storageStatus)}
            </Badge>
          </CardHeader>
          <CardContent>
            <Table>
              <TableBody>
                <TableRow>
                  <TableCell>私有状态</TableCell>
                  <TableCell className="text-right font-mono text-xs">
                    storage/local/app.db
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>可提交模板</TableCell>
                  <TableCell className="text-right font-mono text-xs">
                    storage/templates
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>当前问题</TableCell>
                  <TableCell className="text-right">
                    {validationIssues.length}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function storageStatusLabel(status: string) {
  if (status === "api") {
    return "sqlite";
  }
  if (status === "saving") {
    return "saving";
  }
  if (status === "loading") {
    return "loading";
  }
  if (status === "error") {
    return "local fallback";
  }
  return "local";
}
