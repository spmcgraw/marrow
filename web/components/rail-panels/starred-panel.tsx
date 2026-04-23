"use client";

import { Star } from "lucide-react";

export function StarredPanel() {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
      <Star className="h-6 w-6 text-muted-foreground/60" />
      <div>
        <p className="text-sm font-medium text-foreground">No starred pages</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Star pages from the page menu to keep them one click away.
        </p>
      </div>
    </div>
  );
}
