"use client";

import { useEffect, useRef, useState } from "react";
import { Settings } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

interface Props {
  triggerClassName?: string;
  iconClassName?: string;
}

export function SettingsDialog({ triggerClassName, iconClassName }: Props) {
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
    <div ref={ref} className="relative">
      <button
        type="button"
        title="Settings"
        aria-label="Settings"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground",
          triggerClassName,
        )}
      >
        <Settings className={cn("h-3.5 w-3.5", iconClassName)} />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute bottom-0 left-[calc(100%+8px)] z-50 w-60 rounded-md border border-border bg-popover py-1 shadow-lg"
        >
          <div className="px-3 py-2">
            <p className="text-sm font-medium text-foreground">Settings</p>
            <p className="text-xs text-muted-foreground">Personal preferences.</p>
          </div>
          <div className="my-1 border-t border-border" />
          <div className="flex items-center justify-between px-3 py-1.5">
            <span className="text-sm text-foreground">Appearance</span>
            <ThemeToggle />
          </div>
        </div>
      )}
    </div>
  );
}
