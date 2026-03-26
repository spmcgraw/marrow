"use client";

/**
 * PageEditor — the main editing surface.
 *
 * Uses BlockNote for a Notion-style block editor.
 * Content is serialized to/from Markdown for storage so the export bundle
 * remains human-readable. BlockNote's internal JSON is never persisted.
 *
 * Save behavior: auto-saves 2 seconds after the user stops typing.
 * Each save creates a new revision via PATCH /api/pages/{id}.
 */

import "@blocknote/core/fonts/inter.css";
import "@blocknote/mantine/style.css";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/mantine";
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
  const [status, setStatus] = useState<SaveStatus>("idle");
  const { resolvedTheme } = useTheme();

  // Refs for save logic — avoids stale closures in debounce callbacks
  const titleRef = useRef(title);
  const savedTitleRef = useRef(initialPage.title);
  const savedContentRef = useRef(initialPage.content ?? "");
  const pendingMarkdownRef = useRef(initialPage.content ?? "");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isInitializingRef = useRef(false);

  useEffect(() => {
    titleRef.current = title;
  }, [title]);

  const editor = useCreateBlockNote();

  // Parse initial Markdown content into BlockNote blocks on mount
  useEffect(() => {
    const content = initialPage.content;
    if (!content) return;

    isInitializingRef.current = true;
    const blocks = editor.tryParseMarkdownToBlocks(content);
    editor.replaceBlocks(editor.document, blocks);
    isInitializingRef.current = false;
    pendingMarkdownRef.current = content;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const saveNow = useCallback(async () => {
    const currentTitle = titleRef.current;
    const currentContent = pendingMarkdownRef.current;

    const newTitle = currentTitle !== savedTitleRef.current ? currentTitle : undefined;
    const newContent =
      currentContent !== savedContentRef.current ? currentContent : undefined;

    if (!newTitle && newContent === undefined) return;

    setStatus("saving");
    try {
      await updatePage(initialPage.id, { title: newTitle, content: newContent });
      savedTitleRef.current = currentTitle;
      savedContentRef.current = currentContent;
      setStatus("saved");
      setTimeout(() => setStatus("idle"), 2000);
    } catch (err) {
      toast.error(`Save failed: ${String(err)}`);
      setStatus("error");
    }
  }, [initialPage.id]);

  const scheduleSave = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(saveNow, 2000);
  }, [saveNow]);

  // Debounce save on title change
  useEffect(() => {
    scheduleSave();
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [title, scheduleSave]);

  // Serialize editor blocks to Markdown and schedule a save
  const handleEditorChange = useCallback(() => {
    if (isInitializingRef.current) return;
    const markdown = editor.blocksToMarkdownLossy(editor.document);
    pendingMarkdownRef.current = markdown;
    scheduleSave();
  }, [editor, scheduleSave]);

  // Restore a revision: parse its Markdown into blocks and update editor
  const handleRestore = useCallback(
    async (markdownContent: string) => {
      const blocks = editor.tryParseMarkdownToBlocks(markdownContent);
      editor.replaceBlocks(editor.document, blocks);
      pendingMarkdownRef.current = markdownContent;
      scheduleSave();
    },
    [editor, scheduleSave],
  );

  const statusLabel = {
    idle: "",
    saving: "Saving…",
    saved: "Saved",
    error: "Error saving",
  }[status];

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b px-6 py-2">
        <span className="text-xs text-muted-foreground">{statusLabel}</span>
        <div className="flex gap-2">
          <AttachmentSheet pageId={initialPage.id} collectionId={initialPage.collection_id} />
          <RevisionSheet pageId={initialPage.id} onRestore={handleRestore} />
        </div>
      </div>

      {/* Title */}
      <div className="px-8 pt-8 pb-2">
        <input
          className="w-full bg-transparent text-3xl font-bold outline-none placeholder:text-muted-foreground"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={saveNow}
          placeholder="Untitled"
        />
      </div>

      {/* BlockNote editor */}
      <div className="flex-1 overflow-auto">
        <BlockNoteView
          editor={editor}
          onChange={handleEditorChange}
          theme={resolvedTheme === "dark" ? "dark" : "light"}
          style={{ minHeight: "100%" }}
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
  onRestore: (content: string) => Promise<void>;
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
      <SheetTrigger render={<Button variant="ghost" size="sm" />}>
        <Clock className="mr-1 h-4 w-4" />
        History
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

          {/* Preview — raw Markdown for readability */}
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
                    onClick={async () => {
                      await onRestore(selected.content!);
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
      <SheetTrigger render={<Button variant="ghost" size="sm" />}>
        <Upload className="mr-1 h-4 w-4" />
        Attachments
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
