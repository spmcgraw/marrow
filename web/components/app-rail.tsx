"use client";

import { FolderClosed, Search, Star, Inbox, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import type { User } from "@/lib/types";

export type RailPanel = "pages" | "search" | "starred" | "inbox";

interface Props {
  workspaceName: string;
  panel: RailPanel;
  onPanelChange: (panel: RailPanel) => void;
  user?: User | null;
}

const TABS: Array<{ id: RailPanel; label: string; Icon: typeof FolderClosed }> = [
  { id: "pages", label: "Pages", Icon: FolderClosed },
  { id: "search", label: "Search", Icon: Search },
  { id: "starred", label: "Starred", Icon: Star },
  { id: "inbox", label: "Inbox", Icon: Inbox },
];

function initials(name?: string | null) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  const letters = parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
  return letters || name[0]?.toUpperCase() || "?";
}

export function AppRail({ workspaceName, panel, onPanelChange, user }: Props) {
  return (
    <div className="flex w-14 shrink-0 flex-col items-center gap-1 border-r border-sidebar-border bg-sidebar py-3.5">
      <button
        type="button"
        title={`${workspaceName} workspace`}
        className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-primary font-heading text-[17px] font-medium text-primary-foreground"
      >
        {initials(workspaceName)[0]}
      </button>

      {TABS.map(({ id, label, Icon }) => {
        const active = panel === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => onPanelChange(id)}
            title={label}
            aria-label={label}
            aria-pressed={active}
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-lg transition-colors",
              active
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-foreground",
            )}
          >
            <Icon className="h-4 w-4" />
          </button>
        );
      })}

      <div className="flex-1" />

      <button
        type="button"
        title="Settings"
        aria-label="Settings"
        className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground"
      >
        <Settings className="h-4 w-4" />
      </button>

      {user && (
        <div
          title={user.name}
          className="mt-2 flex h-7 w-7 items-center justify-center rounded-full bg-[#4a6b8a] text-[11px] font-medium text-white"
        >
          {initials(user.name)}
        </div>
      )}
    </div>
  );
}
