"use client";

import * as React from "react";

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
  const [activeView, setActiveView] =
    React.useState<PlatformView>("overview");

  React.useEffect(() => {
    window.scrollTo({ left: 0, top: 0 });
  }, [activeView]);

  return (
    <TradingDataProvider>
      <AppShell activeView={activeView} onViewChange={setActiveView}>
        {activeView === "overview" ? (
          <DashboardView onNavigate={setActiveView} />
        ) : null}
        {activeView === "charts" ? <ChartWorkspace /> : null}
        {activeView === "strategy" ? <StrategyView /> : null}
        {activeView === "ai" ? <AiAdviceView /> : null}
        {activeView === "data" ? <DataManagementView /> : null}
        {activeView === "settings" ? <SettingsView /> : null}
      </AppShell>
    </TradingDataProvider>
  );
}
