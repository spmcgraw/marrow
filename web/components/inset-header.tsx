"use client";

import { useState } from "react";
import { ChevronRight, Eye, MoreHorizontal } from "lucide-react";
import { PageMenu, type PageMenuDrawer } from "@/components/page-menu";
import { useWorkspaceTree, findBreadcrumb } from "@/components/workspace-tree-context";

interface Props {
  collectionId: string;
  pageTitle: string;
  saveLabel: string;
  onOpenDrawer: (which: PageMenuDrawer) => void;
  onShare: () => void;
}

const MOCK_AVATARS = [
  { letter: "A", color: "#8a5a3a" },
  { letter: "S", color: "#3a6b4a" },
  { letter: "L", color: "#4a6b8a" },
];

function Breadcrumbs({ collectionId, pageTitle }: { collectionId: string; pageTitle: string }) {
  const tree = useWorkspaceTree();
  const crumb = tree ? findBreadcrumb(tree, collectionId) : null;
  const parts = crumb
    ? [crumb.spaceName, crumb.collectionName, pageTitle]
    : [pageTitle];

  return (
    <div className="flex min-w-0 flex-1 items-center gap-1.5 font-mono text-[13px] text-muted-foreground">
      {parts.map((part, i) => (
        <span key={i} className="flex min-w-0 items-center gap-1.5">
          <span
            className={`truncate ${
              i === parts.length - 1 ? "text-foreground" : ""
            }`}
          >
            {part}
          </span>
          {i < parts.length - 1 && (
            <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground/60" />
          )}
        </span>
      ))}
    </div>
  );
}

function StackedAvatars() {
  return (
    <div className="flex items-center">
      {MOCK_AVATARS.map((a, i) => (
        <div
          key={a.letter}
          className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-background text-[11px] font-medium text-white"
          style={{
            backgroundColor: a.color,
            marginLeft: i === 0 ? 0 : -6,
          }}
        >
          {a.letter}
        </div>
      ))}
    </div>
  );
}

export function EditorHeader({
  collectionId,
  pageTitle,
  saveLabel,
  onOpenDrawer,
  onShare,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="flex items-center gap-3 border-b border-border px-6 py-3">
      <Breadcrumbs collectionId={collectionId} pageTitle={pageTitle} />

      {saveLabel && (
        <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          {saveLabel}
        </span>
      )}

      <StackedAvatars />

      <button
        type="button"
        onClick={onShare}
        className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
      >
        <Eye className="h-3 w-3" />
        Share
      </button>

      <PageMenu
        open={menuOpen}
        onOpenChange={setMenuOpen}
        onOpenDrawer={(which) => {
          setMenuOpen(false);
          onOpenDrawer(which);
        }}
        trigger={
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            className={`flex h-7 w-7 items-center justify-center rounded-md border transition-colors ${
              menuOpen
                ? "border-primary bg-primary/10 text-primary"
                : "border-transparent text-muted-foreground hover:bg-accent hover:text-foreground"
            }`}
            aria-label="Page menu"
          >
            <MoreHorizontal className="h-3.5 w-3.5" />
          </button>
        }
      />
    </header>
  );
}
