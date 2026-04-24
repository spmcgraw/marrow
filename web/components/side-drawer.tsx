"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { toast } from "sonner";
import { getRevision, listRevisions } from "@/lib/api";
import type { Revision } from "@/lib/types";

export type SideDrawerKind = "backlinks" | "history";

interface Props {
  which: SideDrawerKind;
  pageId: string;
  onClose: () => void;
  onRestore: (content: string, contentFormat: string) => Promise<void>;
}

const TITLES: Record<SideDrawerKind, string> = {
  backlinks: "Backlinks",
  history: "Version history",
};

export function SideDrawer({ which, pageId, onClose, onRestore }: Props) {
  return (
    <aside
      className="absolute inset-y-0 right-0 z-15 flex w-[360px] flex-col border-l border-border bg-card shadow-[-20px_0_40px_-20px_rgba(0,0,0,0.3)]"
      aria-label={TITLES[which]}
    >
      <header className="flex items-center gap-2.5 border-b border-border px-4 py-3">
        <span
          className="text-base font-normal"
          style={{ fontFamily: "var(--font-heading)", fontVariationSettings: '"SOFT" 40' }}
        >
          {TITLES[which]}
        </span>
        <span className="flex-1" />
        <button
          type="button"
          onClick={onClose}
          className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground"
          aria-label="Close drawer"
        >
          <X className="h-3 w-3" />
        </button>
      </header>
      <div className="flex-1 overflow-auto px-4 py-4">
        {which === "backlinks" && <BacklinksEmptyState />}
        {which === "history" && (
          <HistoryList pageId={pageId} onRestore={onRestore} onClose={onClose} />
        )}
      </div>
    </aside>
  );
}

function BacklinksEmptyState() {
  return (
    <div className="rounded-md border border-dashed border-border p-5 text-xs text-muted-foreground">
      <p className="font-medium text-foreground">No backlinks yet.</p>
      <p className="mt-2">
        When another page links here with <span className="font-mono">[[wikilink]]</span>
        {" "}or <span className="font-mono">@mention</span>, it will appear in this panel.
        Backlink indexing is upcoming.
      </p>
    </div>
  );
}

function HistoryList({
  pageId,
  onRestore,
  onClose,
}: {
  pageId: string;
  onRestore: (content: string, contentFormat: string) => Promise<void>;
  onClose: () => void;
}) {
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [selected, setSelected] = useState<Revision | null>(null);
  const [loading, setLoading] = useState(true);
  const [restoring, setRestoring] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const revs = await listRevisions(pageId);
        if (!cancelled) setRevisions(revs);
      } catch {
        if (!cancelled) toast.error("Failed to load revisions");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pageId]);

  async function handleSelect(rev: Revision) {
    try {
      const detail = await getRevision(pageId, rev.id);
      setSelected(detail);
    } catch {
      toast.error("Failed to load revision content");
    }
  }

  async function handleRestore() {
    if (!selected?.content) return;
    setRestoring(true);
    try {
      await onRestore(selected.content, selected.content_format);
      toast.success("Revision restored — save to confirm");
      onClose();
    } finally {
      setRestoring(false);
    }
  }

  if (loading) {
    return <p className="text-xs text-muted-foreground">Loading…</p>;
  }

  if (revisions.length === 0) {
    return <p className="text-xs text-muted-foreground">No revisions yet.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      <ul className="flex flex-col gap-1">
        {revisions.map((rev, i) => {
          const isSelected = selected?.id === rev.id;
          return (
            <li key={rev.id}>
              <button
                type="button"
                onClick={() => handleSelect(rev)}
                className={`w-full rounded-md border px-3 py-2 text-left transition-colors ${
                  isSelected
                    ? "border-primary bg-primary/10"
                    : "border-border hover:bg-accent"
                }`}
              >
                <div className="text-xs font-medium text-foreground">
                  {i === 0 ? "Current" : `Rev ${revisions.length - i}`}
                </div>
                <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                  {new Date(rev.created_at).toLocaleString()}
                </div>
              </button>
            </li>
          );
        })}
      </ul>

      {selected && selected.id !== revisions[0]?.id && (
        <button
          type="button"
          onClick={handleRestore}
          disabled={restoring}
          className="rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          {restoring ? "Restoring…" : "Restore this revision"}
        </button>
      )}
    </div>
  );
}
