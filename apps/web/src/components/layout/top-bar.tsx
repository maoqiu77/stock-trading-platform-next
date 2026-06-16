"use client";

import { MoonIcon, RefreshCwIcon, ShieldCheckIcon, SunIcon } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  getPlatformViewMeta,
  type PlatformView,
} from "@/features/platform/types";

export function TopBar({
  activeView,
  onMarketRefresh,
}: {
  activeView: PlatformView;
  onMarketRefresh: () => void;
}) {
  const { resolvedTheme, setTheme } = useTheme();
  const nextTheme = resolvedTheme === "dark" ? "light" : "dark";
  const viewMeta = getPlatformViewMeta(activeView);

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b bg-background px-3 md:px-4">
      <SidebarTrigger />
      <Separator orientation="vertical" className="h-5" />
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{viewMeta.title}</div>
          <div className="truncate text-xs text-muted-foreground">
            {viewMeta.description}
          </div>
        </div>
      </div>
      <div className="hidden items-center gap-2 text-xs text-muted-foreground md:flex">
        <ShieldCheckIcon />
        <span>storage/local 已隔离</span>
      </div>
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              variant="outline"
              size="icon-sm"
              onClick={onMarketRefresh}
            />
          }
        >
          <RefreshCwIcon />
          <span className="sr-only">刷新</span>
        </TooltipTrigger>
        <TooltipContent>刷新行情</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              variant="outline"
              size="icon-sm"
              onClick={() => setTheme(nextTheme)}
            />
          }
        >
          {resolvedTheme === "dark" ? <SunIcon /> : <MoonIcon />}
          <span className="sr-only">切换主题</span>
        </TooltipTrigger>
        <TooltipContent>切换主题</TooltipContent>
      </Tooltip>
    </header>
  );
}
