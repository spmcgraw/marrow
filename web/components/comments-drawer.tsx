"use client";

import { MessageSquare, Type, Link as LinkIcon, Hash, X } from "lucide-react";

interface Props {
  onClose: () => void;
}

export function CommentsDrawer({ onClose }: Props) {
  return (
    <aside
      className="absolute inset-y-0 right-0 z-15 flex w-[380px] flex-col border-l border-border bg-card shadow-[-20px_0_40px_-20px_rgba(0,0,0,0.3)]"
      aria-label="Comments"
    >
      <header className="flex items-center gap-2.5 border-b border-border px-4 py-3">
        <MessageSquare className="h-4 w-4 text-muted-foreground" />
        <span
          className="font-heading text-base font-normal"
          style={{ fontVariationSettings: '"SOFT" 40' }}
        >
          Comments
        </span>
        <span className="rounded-full border border-border px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
          0 open
        </span>
        <span className="flex-1" />
        <button
          type="button"
          onClick={onClose}
          className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground"
          aria-label="Close comments"
        >
          <X className="h-3 w-3" />
        </button>
      </header>

      <div className="flex-1 overflow-auto px-4 py-5">
        <div className="rounded-md border border-dashed border-border p-5 text-xs text-muted-foreground">
          <p className="font-medium text-foreground">No comments yet.</p>
          <p className="mt-2">
            Leave a comment below to start a thread. Real-time comments ship when
            the backend lands.
          </p>
        </div>
      </div>

      <div className="border-t border-border bg-popover p-3">
        <div className="rounded-md border border-border bg-background px-3 py-2.5">
          <div className="text-[13px] text-muted-foreground">Leave a comment…</div>
          <div className="mt-2.5 flex items-center gap-1.5">
            <button
              type="button"
              className="flex h-6 w-6 items-center justify-center text-muted-foreground hover:text-foreground"
              aria-label="Formatting"
            >
              <Type className="h-3 w-3" />
            </button>
            <button
              type="button"
              className="flex h-6 w-6 items-center justify-center text-muted-foreground hover:text-foreground"
              aria-label="Link"
            >
              <LinkIcon className="h-3 w-3" />
            </button>
            <button
              type="button"
              className="flex h-6 w-6 items-center justify-center text-muted-foreground hover:text-foreground"
              aria-label="Tag"
            >
              <Hash className="h-3 w-3" />
            </button>
            <span className="flex-1" />
            <button
              type="button"
              disabled
              className="rounded-md bg-primary px-3 py-1 text-xs font-medium text-primary-foreground disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
