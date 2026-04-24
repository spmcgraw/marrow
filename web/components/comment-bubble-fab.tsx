"use client";

import { MessageSquare } from "lucide-react";

interface Props {
  onClick: () => void;
  unread?: number;
}

export function CommentBubbleFab({ onClick, unread = 0 }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Open comments"
      className="absolute bottom-6 right-6 z-10 flex h-12 w-12 items-center justify-center rounded-full border border-border bg-card text-muted-foreground shadow-lg transition-colors hover:bg-accent hover:text-foreground"
    >
      <MessageSquare className="h-5 w-5" />
      <span
        className={`absolute -right-0.5 -top-0.5 flex h-5 min-w-[20px] items-center justify-center rounded-full px-1 font-mono text-[10px] font-medium ${
          unread > 0
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground"
        }`}
      >
        {unread}
      </span>
    </button>
  );
}
