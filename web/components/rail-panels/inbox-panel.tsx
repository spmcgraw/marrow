"use client";

import { Inbox } from "lucide-react";

export function InboxPanel() {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
      <Inbox className="h-6 w-6 text-muted-foreground/60" />
      <div>
        <p className="text-sm font-medium text-foreground">Inbox is empty</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Mentions, review requests, and comment replies will show up here.
        </p>
      </div>
    </div>
  );
}
