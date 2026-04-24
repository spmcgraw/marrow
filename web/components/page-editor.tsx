"use client";

/**
 * PageEditor — the main editing surface.
 *
 * Uses BlockNote for a Notion-style block editor. Content is stored as
 * BlockNote JSON (content_format='json') for new saves. Legacy Markdown
 * revisions (content_format='markdown') are read-only-parsed on load for
 * backward compatibility.
 *
 * Features:
 * - Code blocks with Shiki syntax highlighting
 * - Tables with drag handles (TableHandlesController)
 * - @-mention page links via suggestion menu (SuggestionMenuController)
 * - Auto-save 2 seconds after last keystroke
 */

import "@blocknote/core/fonts/inter.css";
import "@blocknote/mantine/style.css";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { useTheme } from "next-themes";
import {
  BlockNoteSchema,
  createCodeBlockSpec,
  defaultBlockSpecs,
} from "@blocknote/core";
import { filterSuggestionItems } from "@blocknote/core/extensions";
import {
  SuggestionMenuController,
  TableHandlesController,
  getDefaultReactSlashMenuItems,
  useCreateBlockNote,
  type DefaultReactSuggestionItem,
} from "@blocknote/react";
import { calloutBlockSpec, calloutSlashMenuItem } from "@/components/editor/callout-block";
import { BlockNoteView } from "@blocknote/mantine";
import { createHighlighter } from "shiki";
import { Upload } from "lucide-react";
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
import { EditorHeader } from "@/components/inset-header";
import { SideDrawer, type SideDrawerKind } from "@/components/side-drawer";
import { CommentsDrawer } from "@/components/comments-drawer";
import { CommentBubbleFab } from "@/components/comment-bubble-fab";
import {
  attachmentFileUrl,
  listAttachments,
  searchWorkspace,
  updatePage,
  uploadAttachment,
} from "@/lib/api";
import type { Attachment, Page } from "@/lib/types";

type SaveStatus = "idle" | "saving" | "saved" | "error";

interface Props {
  initialPage: Page;
}

// ---------------------------------------------------------------------------
// BlockNote schema with Shiki syntax highlighting for code blocks
// ---------------------------------------------------------------------------

const schema = BlockNoteSchema.create({
  blockSpecs: {
    ...defaultBlockSpecs,
    codeBlock: createCodeBlockSpec({
      createHighlighter: () =>
        createHighlighter({
          themes: ["github-light", "github-dark"],
          langs: [
            "javascript",
            "typescript",
            "python",
            "bash",
            "json",
            "html",
            "css",
            "sql",
            "go",
            "rust",
            "yaml",
            "markdown",
          ],
        }),
      defaultLanguage: "text",
    }),
    callout: calloutBlockSpec(),
  },
});

// ---------------------------------------------------------------------------
// PageEditor component
// ---------------------------------------------------------------------------

export function PageEditor({ initialPage }: Props) {
  const [title, setTitle] = useState(initialPage.title);
  const [status, setStatus] = useState<SaveStatus>("idle");
  const { resolvedTheme } = useTheme();

  // Extract workspaceId from the URL for page mention search
  const params = useParams<{ workspaceId?: string }>();
  const workspaceId = params?.workspaceId;

  // Refs for save logic — avoids stale closures in debounce callbacks
  const titleRef = useRef(title);
  const savedTitleRef = useRef(initialPage.title);
  const savedContentRef = useRef(initialPage.content ?? "");
  // pendingContentRef holds the current JSON string to save
  const pendingContentRef = useRef(initialPage.content ?? "");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isInitializingRef = useRef(false);

  useEffect(() => {
    titleRef.current = title;
  }, [title]);

  const editor = useCreateBlockNote({ schema });

  // Load initial content — JSON (new format) or Markdown (legacy)
  useEffect(() => {
    const content = initialPage.content;
    if (!content) return;

    isInitializingRef.current = true;

    const fmt = initialPage.content_format ?? "markdown";
    if (fmt === "json") {
      try {
        const blocks = JSON.parse(content);
        editor.replaceBlocks(editor.document, blocks);
        pendingContentRef.current = content;
      } catch {
        // Malformed JSON: fall back to showing raw text
        pendingContentRef.current = content;
      }
    } else {
      // Legacy Markdown: parse into blocks
      const blocks = editor.tryParseMarkdownToBlocks(content);
      editor.replaceBlocks(editor.document, blocks);
      // On first save this will be re-serialized as JSON
      pendingContentRef.current = content;
    }

    isInitializingRef.current = false;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const saveNow = useCallback(async () => {
    const currentTitle = titleRef.current;
    const currentContent = pendingContentRef.current;

    const newTitle = currentTitle !== savedTitleRef.current ? currentTitle : undefined;
    const newContent =
      currentContent !== savedContentRef.current ? currentContent : undefined;

    if (!newTitle && newContent === undefined) return;

    setStatus("saving");
    try {
      await updatePage(initialPage.id, {
        title: newTitle,
        content: newContent,
        content_format: "json",
      });
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

  // Serialize editor document to JSON and schedule a save
  const handleEditorChange = useCallback(() => {
    if (isInitializingRef.current) return;
    const json = JSON.stringify(editor.document);
    pendingContentRef.current = json;
    scheduleSave();
  }, [editor, scheduleSave]);

  // Restore a revision into the editor
  const handleRestore = useCallback(
    async (content: string, contentFormat: string) => {
      if (contentFormat === "json") {
        try {
          const blocks = JSON.parse(content);
          editor.replaceBlocks(editor.document, blocks);
          pendingContentRef.current = content;
        } catch {
          toast.error("Could not parse revision content");
          return;
        }
      } else {
        // Legacy markdown revision
        const blocks = editor.tryParseMarkdownToBlocks(content);
        editor.replaceBlocks(editor.document, blocks);
        // Re-serialize as JSON for the next save
        pendingContentRef.current = JSON.stringify(editor.document);
      }
      scheduleSave();
    },
    [editor, scheduleSave],
  );

  // ---------------------------------------------------------------------------
  // @-mention suggestion menu — queries workspace pages
  // ---------------------------------------------------------------------------

  const getPageMentionItems = useCallback(
    async (query: string): Promise<DefaultReactSuggestionItem[]> => {
      if (!workspaceId) return [];
      try {
        const { results } = await searchWorkspace(workspaceId, query);
        return results.slice(0, 8).map((result) => ({
          title: result.title,
          subtext: `${result.space_name} / ${result.collection_name}`,
          onItemClick: () => {
            editor.createLink(`/w/${workspaceId}/pages/${result.page_id}`, result.title);
          },
        }));
      } catch {
        return [];
      }
    },
    [editor, workspaceId],
  );

  const statusLabel = {
    idle: "",
    saving: "Saving…",
    saved: "Saved",
    error: "Error saving",
  }[status];

  const [sideDrawer, setSideDrawer] = useState<SideDrawerKind | null>(null);
  const [commentsOpen, setCommentsOpen] = useState(false);

  function handleOpenDrawer(which: SideDrawerKind) {
    setCommentsOpen(false);
    setSideDrawer(which);
  }

  function handleShareStub() {
    toast.info("Sharing lands with #40");
  }

  return (
    <div className="relative flex h-full flex-col">
      <EditorHeader
        collectionId={initialPage.collection_id}
        pageTitle={title || "Untitled"}
        saveLabel={statusLabel}
        onOpenDrawer={handleOpenDrawer}
        onShare={handleShareStub}
      />

      {/* Attachments — retained while Phase A omits an Attachments menu entry */}
      <div className="flex items-center border-b border-border px-6 py-1.5">
        <AttachmentSheet pageId={initialPage.id} collectionId={initialPage.collection_id} />
      </div>

      {/* Title */}
      <div className="px-10 pt-14 pb-2">
        <input
          className="w-full bg-transparent font-heading outline-none placeholder:text-muted-foreground"
          style={{
            fontSize: 40,
            fontWeight: 400,
            letterSpacing: "-0.015em",
            fontVariationSettings: '"SOFT" 60',
          }}
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
        >
          {/* Table drag handles */}
          <TableHandlesController />

          {/* Slash menu — default items + callout */}
          <SuggestionMenuController
            triggerCharacter="/"
            getItems={async (query) =>
              filterSuggestionItems(
                [...getDefaultReactSlashMenuItems(editor), calloutSlashMenuItem(editor)],
                query,
              )
            }
          />

          {/* @-mention suggestion menu for page links */}
          <SuggestionMenuController
            triggerCharacter="@"
            getItems={getPageMentionItems}
          />
        </BlockNoteView>
      </div>

      {!commentsOpen && (
        <CommentBubbleFab onClick={() => { setSideDrawer(null); setCommentsOpen(true); }} />
      )}

      {sideDrawer && (
        <SideDrawer
          which={sideDrawer}
          pageId={initialPage.id}
          onClose={() => setSideDrawer(null)}
          onRestore={handleRestore}
        />
      )}

      {commentsOpen && <CommentsDrawer onClose={() => setCommentsOpen(false)} />}
    </div>
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
