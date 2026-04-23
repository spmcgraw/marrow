"use client";

import { useEffect, useRef, useState } from "react";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppRail, type RailPanel } from "@/components/app-rail";
import { AppSidebar } from "@/components/app-sidebar";
import { WorkspaceTreeProvider } from "@/components/workspace-tree-context";
import type { User, WorkspaceTree } from "@/lib/types";

interface Props {
  tree: WorkspaceTree;
  user: User | null;
  memberCount: number | null;
  children: React.ReactNode;
}

export function WorkspaceShell({ tree, user, memberCount, children }: Props) {
  const [panel, setPanel] = useState<RailPanel>("pages");
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPanel("search");
        requestAnimationFrame(() => searchInputRef.current?.focus());
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <SidebarProvider>
      <div className="flex h-svh w-full overflow-hidden bg-background text-foreground">
        <AppRail
          workspaceName={tree.name}
          panel={panel}
          onPanelChange={setPanel}
          user={user}
        />
        <AppSidebar
          tree={tree}
          user={user}
          panel={panel}
          memberCount={memberCount}
          searchInputRef={searchInputRef}
        />
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <WorkspaceTreeProvider tree={tree}>{children}</WorkspaceTreeProvider>
        </main>
      </div>
    </SidebarProvider>
  );
}
