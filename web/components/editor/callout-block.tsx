"use client";

import { createReactBlockSpec } from "@blocknote/react";
import { insertOrUpdateBlockForSlashMenu } from "@blocknote/core/extensions";
import { Sparkle } from "lucide-react";
import type { DefaultReactSuggestionItem } from "@blocknote/react";

export const calloutBlockSpec = createReactBlockSpec(
  {
    type: "callout",
    propSchema: {
      label: { default: "Note" },
    },
    content: "inline",
  },
  {
    render: ({ block, contentRef }) => {
      const label = (block.props as { label?: string }).label ?? "Note";
      return (
        <div
          className="flex gap-3.5 rounded-lg border px-4 py-3.5"
          style={{
            background: "color-mix(in oklab, var(--primary) 10%, transparent)",
            borderColor: "color-mix(in oklab, var(--primary) 40%, transparent)",
          }}
        >
          <Sparkle className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
          <div className="min-w-0 flex-1">
            <div className="mb-1 font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-primary">
              {label}
            </div>
            <div
              ref={contentRef}
              className="text-[14.5px] leading-[1.6] text-foreground"
            />
          </div>
        </div>
      );
    },
  },
);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function calloutSlashMenuItem(editor: any): DefaultReactSuggestionItem {
  return {
    title: "Callout",
    subtext: "Highlight a note, warning, or pull-quote",
    aliases: ["note", "warning", "tip", "admonition"],
    group: "Basic blocks",
    onItemClick: () => {
      insertOrUpdateBlockForSlashMenu(editor, { type: "callout" });
    },
  };
}
