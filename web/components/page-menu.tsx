"use client";

import { useEffect, useRef } from "react";
import {
  ArrowRight,
  BookOpen,
  Copy,
  Eye,
  History,
  Link as LinkIcon,
  Star,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

export type PageMenuDrawer = "backlinks" | "history";

type Item =
  | { kind: "divider" }
  | {
      kind: "drawer";
      id: PageMenuDrawer;
      icon: React.ComponentType<{ className?: string }>;
      label: string;
      meta?: string;
    }
  | {
      kind: "action";
      id: string;
      icon: React.ComponentType<{ className?: string }>;
      label: string;
      meta?: string;
      destructive?: boolean;
    };

const ITEMS: Item[] = [
  { kind: "drawer", id: "backlinks", icon: LinkIcon, label: "Backlinks", meta: "0" },
  { kind: "drawer", id: "history", icon: History, label: "Version history" },
  { kind: "divider" },
  { kind: "action", id: "star", icon: Star, label: "Star", meta: "⌥S" },
  { kind: "action", id: "watch", icon: Eye, label: "Watch" },
  { kind: "divider" },
  { kind: "action", id: "duplicate", icon: Copy, label: "Duplicate" },
  { kind: "action", id: "move", icon: ArrowRight, label: "Move…" },
  { kind: "action", id: "export", icon: BookOpen, label: "Export as Markdown" },
  { kind: "divider" },
  { kind: "action", id: "archive", icon: Trash2, label: "Archive", destructive: true },
];

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenDrawer: (which: PageMenuDrawer) => void;
  trigger: React.ReactNode;
}

export function PageMenu({ open, onOpenChange, onOpenDrawer, trigger }: Props) {
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (!wrapperRef.current?.contains(e.target as Node)) {
        onOpenChange(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open, onOpenChange]);

  return (
    <div ref={wrapperRef} className="relative">
      {trigger}
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-9 z-20 w-60 rounded-lg border border-border bg-popover p-1.5 shadow-[0_20px_40px_-15px_rgba(0,0,0,0.5)]"
        >
          {ITEMS.map((item, i) => {
            if (item.kind === "divider") {
              return <div key={`div-${i}`} className="my-1 h-px bg-border" />;
            }

            const Icon = item.icon;
            const destructive = item.kind === "action" && item.destructive;

            return (
              <button
                key={item.id}
                type="button"
                role="menuitem"
                onClick={() => {
                  if (item.kind === "drawer") {
                    onOpenDrawer(item.id);
                  } else {
                    toast.info(`${item.label} — coming soon`);
                    onOpenChange(false);
                  }
                }}
                className={`flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-accent ${
                  destructive ? "text-destructive" : "text-foreground"
                }`}
              >
                <Icon
                  className={`h-3.5 w-3.5 shrink-0 ${
                    destructive ? "text-destructive" : "text-muted-foreground"
                  }`}
                />
                <span className="flex-1">{item.label}</span>
                {item.meta && (
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {item.meta}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
