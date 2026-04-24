"use client";

import { useEffect, useRef, useState } from "react";
import { FolderClosed, Search, Star, Inbox, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { SettingsDialog } from "@/components/settings-dialog";
import { logout } from "@/lib/api";
import type { User } from "@/lib/types";

export type RailPanel = "pages" | "search" | "starred" | "inbox";

interface Props {
  workspaceName: string;
  panel: RailPanel;
  onPanelChange: (panel: RailPanel) => void;
  sidebarOpen: boolean;
  onSidebarToggle: () => void;
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

export function AppRail({
  workspaceName,
  panel,
  onPanelChange,
  sidebarOpen,
  onSidebarToggle,
  user,
}: Props) {
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
        const active = panel === id && sidebarOpen;
        return (
          <button
            key={id}
            type="button"
            onClick={() => {
              if (panel === id) {
                onSidebarToggle();
              } else {
                onPanelChange(id);
                if (!sidebarOpen) onSidebarToggle();
              }
            }}
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

      <SettingsDialog
        triggerClassName="h-9 w-9 rounded-lg"
        iconClassName="h-4 w-4"
      />

      {user && <UserMenu user={user} />}
    </div>
  );
}

function UserMenu({ user }: { user: User }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  return (
    <div ref={ref} className="relative mt-2">
      <button
        type="button"
        title={user.name}
        aria-label="Account menu"
        onClick={() => setOpen((v) => !v)}
        className="flex h-7 w-7 items-center justify-center rounded-full bg-[#4a6b8a] text-[11px] font-medium text-white outline-none ring-offset-2 ring-offset-sidebar focus-visible:ring-2 focus-visible:ring-primary"
      >
        {initials(user.name)}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute bottom-0 left-[calc(100%+8px)] z-50 w-60 rounded-md border border-border bg-popover py-1 shadow-lg"
        >
          <div className="px-3 py-2">
            <p className="truncate text-sm font-medium text-foreground">{user.name}</p>
            <p className="truncate text-xs text-muted-foreground">{user.email}</p>
          </div>
          <div className="my-1 border-t border-border" />
          <button
            type="button"
            role="menuitem"
            onClick={async () => {
              setOpen(false);
              const logoutUrl = await logout();
              window.location.href = logoutUrl ?? "/login";
            }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-foreground hover:bg-accent"
          >
            <LogOut className="h-3.5 w-3.5 text-muted-foreground" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
