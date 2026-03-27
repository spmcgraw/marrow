"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { searchWorkspace } from "@/lib/api";
import type { SearchResultItem } from "@/lib/types";

interface Props {
  workspaceId: string;
}

function HighlightedSnippet({ text }: { text: string }) {
  const parts = text.split("**");
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <strong key={i} className="text-foreground font-semibold">
            {part}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

export function SearchDialog({ workspaceId }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [isMac, setIsMac] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    setIsMac(navigator.platform.toUpperCase().includes("MAC"));
  }, []);

  // Global keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (!open) {
      setQuery("");
      setResults([]);
      setActiveIndex(0);
    }
  }, [open]);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setActiveIndex(0);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await searchWorkspace(workspaceId, query.trim());
        setResults(res.results);
        setActiveIndex(0);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query, workspaceId]);

  // Scroll active result into view
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const active = list.children[activeIndex] as HTMLElement | undefined;
    active?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  const navigateToResult = useCallback(
    (result: SearchResultItem) => {
      setOpen(false);
      router.push(`/w/${workspaceId}/pages/${result.page_id}`);
    },
    [workspaceId, router]
  );

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[activeIndex]) {
      e.preventDefault();
      navigateToResult(results[activeIndex]);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex w-full items-center gap-2 rounded-md border border-input bg-background px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
      >
        <Search className="h-3.5 w-3.5" />
        <span className="flex-1 text-left">Search...</span>
        <kbd className="pointer-events-none hidden select-none items-center gap-0.5 rounded border bg-muted px-1 font-mono text-[10px] font-medium sm:flex">
          {isMac ? "\u2318K" : "Ctrl+K"}
        </kbd>
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          showCloseButton={false}
          className="top-[20%] -translate-y-0 sm:max-w-lg p-0 gap-0 overflow-hidden"
        >
          <div className="flex items-center border-b px-3">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <Input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search pages..."
              className="border-0 focus-visible:ring-0 focus-visible:ring-offset-0 h-11 text-sm"
              autoFocus
            />
          </div>

          {query.trim() && (
            <div ref={listRef} className="max-h-72 overflow-y-auto p-1">
              {loading && results.length === 0 && (
                <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                  Searching...
                </p>
              )}
              {!loading && results.length === 0 && (
                <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                  No results found.
                </p>
              )}
              {results.map((result, i) => (
                <button
                  key={result.page_id}
                  type="button"
                  onClick={() => navigateToResult(result)}
                  onMouseEnter={() => setActiveIndex(i)}
                  className={`flex w-full flex-col gap-0.5 rounded-md px-3 py-2 text-left text-sm transition-colors ${
                    i === activeIndex
                      ? "bg-accent text-accent-foreground"
                      : "text-foreground hover:bg-accent/50"
                  }`}
                >
                  <span className="font-medium">{result.title}</span>
                  <span className="text-xs text-muted-foreground">
                    {result.space_name} / {result.collection_name}
                  </span>
                  <span className="text-xs text-muted-foreground line-clamp-2">
                    <HighlightedSnippet text={result.snippet} />
                  </span>
                </button>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}