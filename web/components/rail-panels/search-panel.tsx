"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { searchWorkspace } from "@/lib/api";
import type { SearchResultItem } from "@/lib/types";
import { Input } from "@/components/ui/input";

interface Props {
  workspaceId: string;
  inputRef?: React.RefObject<HTMLInputElement | null>;
}

function HighlightedSnippet({ text }: { text: string }) {
  const parts = text.split("**");
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <strong key={i} className="font-semibold text-foreground">
            {part}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

export function SearchPanel({ workspaceId, inputRef: externalRef }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [tookMs, setTookMs] = useState<number | null>(null);
  const startedAt = useRef<number>(0);
  const router = useRouter();

  useEffect(() => {
    if (!query.trim()) return;
    const timer = setTimeout(async () => {
      setLoading(true);
      startedAt.current = performance.now();
      try {
        const res = await searchWorkspace(workspaceId, query.trim());
        setResults(res.results);
        setActiveIndex(0);
        setTookMs(Math.round(performance.now() - startedAt.current));
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [query, workspaceId]);

  const trimmed = query.trim();
  const visibleResults = trimmed ? results : [];

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[activeIndex]) {
      e.preventDefault();
      router.push(`/w/${workspaceId}/pages/${results[activeIndex].page_id}`);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-3 pb-3">
      <Input
        ref={externalRef}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Search pages..."
        autoFocus
        className="border-primary/50 focus-visible:ring-primary/40"
      />
      {trimmed && (
        <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          {loading
            ? "Searching…"
            : `${visibleResults.length} result${visibleResults.length === 1 ? "" : "s"}${tookMs !== null ? ` · ${tookMs}ms` : ""}`}
        </div>
      )}
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
        {trimmed && !loading && visibleResults.length === 0 && (
          <p className="text-xs text-muted-foreground">No results found.</p>
        )}
        {visibleResults.map((r, i) => (
          <button
            key={r.page_id}
            type="button"
            onClick={() => router.push(`/w/${workspaceId}/pages/${r.page_id}`)}
            onMouseEnter={() => setActiveIndex(i)}
            className={`rounded-md border border-border px-3 py-2 text-left transition-colors ${
              i === activeIndex ? "bg-accent" : "bg-background hover:bg-accent/60"
            }`}
          >
            <div className="text-sm font-medium text-foreground">{r.title}</div>
            <div className="mt-1 font-mono text-[11px] text-muted-foreground">
              {r.space_name} / {r.collection_name}
            </div>
            <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">
              <HighlightedSnippet text={r.snippet} />
            </div>
          </button>
        ))}
        {!trimmed && (
          <p className="text-xs text-muted-foreground">
            Search titles and page content across this workspace.
          </p>
        )}
      </div>
    </div>
  );
}
