"use client";

import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";

import { AppShell } from "@/components/layout/app-shell";
import { ChartWorkspace } from "@/features/charts/chart-workspace";
import { AiAdviceView } from "@/features/platform/views/ai-advice-view";
import { DashboardView } from "@/features/platform/views/dashboard-view";
import { DataManagementView } from "@/features/platform/views/data-management-view";
import { SettingsView } from "@/features/platform/views/settings-view";
import { StrategyView } from "@/features/platform/views/strategy-view";
import { TradingDataProvider } from "@/features/platform/trading-data-context";
import type { PlatformView } from "@/features/platform/types";

export function PlatformWorkspace() {
  const queryClient = useQueryClient();
  const [activeView, setActiveView] =
    React.useState<PlatformView>("overview");
  const [marketRefreshKey, setMarketRefreshKey] = React.useState(0);

  const refreshMarketData = React.useCallback(() => {
    setMarketRefreshKey((current) => current + 1);
    queryClient.invalidateQueries({ queryKey: ["signals"] });
    queryClient.invalidateQueries({ queryKey: ["chart"] });
  }, [queryClient]);

  React.useEffect(() => {
    window.scrollTo({ left: 0, top: 0 });
  }, [activeView]);

  return (
    <TradingDataProvider>
      <AppShell
        activeView={activeView}
        onMarketRefresh={refreshMarketData}
        onViewChange={setActiveView}
      >
        {activeView === "overview" ? (
          <DashboardView
            marketRefreshKey={marketRefreshKey}
            onNavigate={setActiveView}
          />
        ) : null}
        {activeView === "charts" ? (
          <ChartWorkspace marketRefreshKey={marketRefreshKey} />
        ) : null}
        {activeView === "strategy" ? <StrategyView /> : null}
        {activeView === "ai" ? <AiAdviceView /> : null}
        {activeView === "data" ? <DataManagementView /> : null}
        {activeView === "settings" ? <SettingsView /> : null}
      </AppShell>
    </TradingDataProvider>
  );
}
