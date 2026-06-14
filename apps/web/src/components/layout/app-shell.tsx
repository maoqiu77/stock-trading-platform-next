"use client";

import * as React from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { TopBar } from "@/components/layout/top-bar";
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar";
import type { PlatformView } from "@/features/platform/types";

export function AppShell({
  activeView,
  onViewChange,
  children,
}: {
  activeView: PlatformView;
  onViewChange: (view: PlatformView) => void;
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider defaultOpen>
      <AppSidebar activeView={activeView} onViewChange={onViewChange} />
      <SidebarInset>
        <TopBar activeView={activeView} />
        <main className="min-h-[calc(100svh-3.5rem)] bg-background p-3 md:p-4">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
