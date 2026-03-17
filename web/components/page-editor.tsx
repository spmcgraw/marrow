"use client";

/**
 * PageEditor — the main editing surface.
 *
 * Uses a plain <textarea> for Markdown input.
 * TODO: replace the textarea with a Tiptap editor once the data flow is stable.
 *
 * Save behavior: auto-saves 2 seconds after the user stops typing, and on blur.
 * Each save creates a new revision via PATCH /api/pages/{id}.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Clock, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  attachmentFileUrl,
  getRevision,
  listAttachments,
  listRevisions,
  updatePage,
  uploadAttachment,
} from "@/lib/api";
import type { Attachment, Page, Revision } from "@/lib/types";

type SaveStatus = "idle" | "saving" | "saved" | "error";

interface Props {
  initialPage: Page;
}

export function PageEditor({ initialPage }: Props) {
  const [title, setTitle] = useState(initialPage.title);
  const [content, setContent] = useState(initialPage.content ?? "");
  const [status, setStatus] = useState<SaveStatus>("idle");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const savedTitleRef = useRef(initialPage.title);
  const savedContentRef = useRef(initialPage.content ?? "");

  const save = useCallback(async () => {
    const newTitle = title !== savedTitleRef.current ? title : undefined;
    const newContent = content !== savedContentRef.current ? content : undefined;

    if (!newTitle && newContent === undefined) return;

    setStatus("saving");
    try {
      await updatePage(initialPage.id, { title: newTitle, content: newContent });
      savedTitleRef.current = title;
      savedContentRef.current = content;
      setStatus("saved");
      setTimeout(() => setStatus("idle"), 2000);
    } catch (err) {
      toast.error(`Save failed: ${String(err)}`);
      setStatus("error");
    }
  }, [initialPage.id, title, content]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(save, 2000);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [title, content, save]);

  const statusLabel = { idle: "", saving: "Saving…", saved: "Saved", error: "Error saving" }[status];

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b px-6 py-2">
        <span className="text-xs text-muted-foreground">{statusLabel}</span>
        <div className="flex gap-2">
          <AttachmentSheet pageId={initialPage.id} collectionId={initialPage.collection_id} />
          <RevisionSheet pageId={initialPage.id} onRestore={(c) => setContent(c)} />
        </div>
      </div>

      {/* Title */}
      <div className="px-8 pt-8">
        <input
          className="w-full bg-transparent text-3xl font-bold outline-none placeholder:text-muted-foreground"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={save}
          placeholder="Untitled"
        />
      </div>

      {/* Editor — plain textarea; Tiptap replaces this later */}
      <div className="flex-1 px-8 py-4">
        <textarea
          className="h-full w-full resize-none bg-transparent font-mono text-sm leading-relaxed outline-none placeholder:text-muted-foreground"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onBlur={save}
          placeholder="Start writing in Markdown…"
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Revision history panel
// ---------------------------------------------------------------------------

function RevisionSheet({
  pageId,
  onRestore,
}: {
  pageId: string;
  onRestore: (content: string) => void;
}) {
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [selected, setSelected] = useState<Revision | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const revs = await listRevisions(pageId);
      setRevisions(revs);
    } catch {
      toast.error("Failed to load revisions");
    } finally {
      setLoading(false);
    }
  }

  async function selectRevision(rev: Revision) {
    try {
      const detail = await getRevision(pageId, rev.id);
      setSelected(detail);
    } catch {
      toast.error("Failed to load revision content");
    }
  }

  return (
    <Sheet onOpenChange={(open) => open && load()}>
      {/* Base UI uses render prop instead of asChild */}
      <SheetTrigger render={<span />}>
        <Button variant="ghost" size="sm" onClick={() => {}}>
          <Clock className="mr-1 h-4 w-4" />
          History
        </Button>
      </SheetTrigger>
      <SheetContent className="flex flex-col gap-0 p-0 sm:max-w-lg">
        <SheetHeader className="border-b px-4 py-3">
          <SheetTitle>Revision History</SheetTitle>
        </SheetHeader>
        <div className="flex flex-1 overflow-hidden">
          {/* Revision list */}
          <ScrollArea className="w-44 border-r">
            {loading && <p className="px-3 py-2 text-xs text-muted-foreground">Loading…</p>}
            {revisions.map((rev, i) => (
              <button
                key={rev.id}
                onClick={() => selectRevision(rev)}
                className={`w-full px-3 py-2 text-left text-xs hover:bg-accent ${
                  selected?.id === rev.id ? "bg-accent" : ""
                }`}
              >
                <p className="font-medium">{i === 0 ? "Current" : `Rev ${revisions.length - i}`}</p>
                <p className="text-muted-foreground">
                  {new Date(rev.created_at).toLocaleString()}
                </p>
              </button>
            ))}
          </ScrollArea>

          {/* Preview */}
          <div className="flex flex-1 flex-col overflow-hidden">
            {selected ? (
              <>
                <ScrollArea className="flex-1 p-3">
                  <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed">
                    {selected.content}
                  </pre>
                </ScrollArea>
                <div className="border-t p-3">
                  <Button
                    size="sm"
                    className="w-full"
                    onClick={() => {
                      onRestore(selected.content!);
                      toast.success("Revision restored — save to confirm");
                    }}
                  >
                    Restore this revision
                  </Button>
                </div>
              </>
            ) : (
              <p className="p-3 text-xs text-muted-foreground">
                Select a revision to preview it.
              </p>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

// ---------------------------------------------------------------------------
// Attachment panel
// ---------------------------------------------------------------------------

function AttachmentSheet({
  pageId,
  collectionId,
}: {
  pageId: string;
  collectionId: string;
}) {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      const atts = await listAttachments(collectionId, pageId);
      setAttachments(atts);
    } catch {
      toast.error("Failed to load attachments");
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadAttachment(collectionId, pageId, file);
      await load();
      toast.success(`${file.name} uploaded`);
    } catch (err) {
      toast.error(`Upload failed: ${String(err)}`);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <Sheet onOpenChange={(open) => open && load()}>
      <SheetTrigger render={<span />}>
        <Button variant="ghost" size="sm" onClick={() => {}}>
          <Upload className="mr-1 h-4 w-4" />
          Attachments
        </Button>
      </SheetTrigger>
      <SheetContent className="flex flex-col gap-0 p-0">
        <SheetHeader className="border-b px-4 py-3">
          <SheetTitle>Attachments</SheetTitle>
        </SheetHeader>
        <ScrollArea className="flex-1 p-4">
          {attachments.length === 0 && (
            <p className="text-xs text-muted-foreground">No attachments yet.</p>
          )}
          {attachments.map((att) => (
            <div
              key={att.id}
              className="mb-2 flex items-center justify-between rounded border px-3 py-2"
            >
              <div>
                <p className="text-sm font-medium">{att.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {(att.size_bytes / 1024).toFixed(1)} KB
                </p>
              </div>
              <a
                href={attachmentFileUrl(collectionId, pageId, att.id)}
                className="text-xs text-blue-600 hover:underline"
                download={att.filename}
              >
                Download
              </a>
            </div>
          ))}
        </ScrollArea>
        <div className="border-t p-4">
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
          <Button
            className="w-full"
            variant="outline"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "Uploading…" : "Upload file"}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
