"use client";

import { Link as LinkIcon } from "lucide-react";
import type { DefaultReactSuggestionItem } from "@blocknote/react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function pageLinkSlashMenuItem(_editor: any, openPicker: () => void): DefaultReactSuggestionItem {
  return {
    title: "Page link",
    subtext: "Link to another page in this workspace",
    aliases: ["page", "link", "ref", "wiki"],
    group: "Custom",
    icon: <LinkIcon className="h-4 w-4" />,
    onItemClick: () => {
      // Defer so the slash-menu finishes closing and the editor selection
      // is restored before we re-focus into the picker.
      setTimeout(openPicker, 0);
    },
  };
}
