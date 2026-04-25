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
  defaultInlineContentSpecs,
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
import { mentionInlineContentSpec } from "@/components/editor/mention-inline-content";
import { pageLinkSlashMenuItem } from "@/components/editor/page-link-slash-item";
import { useWorkspaceTree } from "@/components/workspace-tree-context";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
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
  listOrgMembers,
  searchWorkspace,
  updatePage,
  uploadAttachment,
} from "@/lib/api";
import type { Attachment, OrgMembership, Page, SearchResultItem } from "@/lib/types";

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
  inlineContentSpecs: {
    ...defaultInlineContentSpecs,
    mention: mentionInlineContentSpec,
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
  const titleInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("new") !== "1") return;
    titleInputRef.current?.focus();
    titleInputRef.current?.select();
    params.delete("new");
    const qs = params.toString();
    window.history.replaceState(
      null,
      "",
      window.location.pathname + (qs ? `?${qs}` : "")
    );
  }, [initialPage.id]);

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

  // Load initial content — JSON (new format) or Markdown (legacy).
  // Deferred to a microtask so BlockNote's internal flushSync doesn't fire
  // while React is still committing the initial render (React 19).
  useEffect(() => {
    const content = initialPage.content;
    if (!content) return;

    let cancelled = false;
    queueMicrotask(async () => {
      if (cancelled) return;
      isInitializingRef.current = true;
      const fmt = initialPage.content_format ?? "markdown";
      try {
        if (fmt === "json") {
          const blocks = JSON.parse(content);
          editor.replaceBlocks(editor.document, blocks);
        } else {
          const blocks = await editor.tryParseMarkdownToBlocks(content);
          editor.replaceBlocks(editor.document, blocks);
        }
        pendingContentRef.current = content;
      } catch {
        pendingContentRef.current = content;
      } finally {
        isInitializingRef.current = false;
      }
    });

    return () => {
      cancelled = true;
    };
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
  // @-mention suggestion menu — queries workspace members
  // ---------------------------------------------------------------------------

  const tree = useWorkspaceTree();
  const orgId = tree?.org_id ?? null;
  const membersCacheRef = useRef<{ orgId: string; members: OrgMembership[] } | null>(null);

  const getMemberItems = useCallback(
    async (query: string): Promise<DefaultReactSuggestionItem[]> => {
      if (!orgId) return [];
      let members: OrgMembership[];
      if (membersCacheRef.current?.orgId === orgId) {
        members = membersCacheRef.current.members;
      } else {
        try {
          members = await listOrgMembers(orgId);
          membersCacheRef.current = { orgId, members };
        } catch {
          return [];
        }
      }

      const q = query.trim().toLowerCase();
      const filtered = q
        ? members.filter(
            (m) => m.email.toLowerCase().includes(q),
          )
        : members;

      return filtered.slice(0, 8).map((member) => {
        const displayName = member.email.split("@")[0] || member.email;
        return {
          title: displayName,
          subtext: member.email,
          onItemClick: () => {
            editor.insertInlineContent([
              {
                type: "mention",
                props: { userId: member.user_id ?? "", displayName },
              },
              " ",
            ]);
          },
        };
      });
    },
    [editor, orgId],
  );

  // ---------------------------------------------------------------------------
  // /page slash item — opens a page picker that inserts a WikiLink
  // ---------------------------------------------------------------------------

  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerQuery, setPickerQuery] = useState("");
  const [pickerResults, setPickerResults] = useState<SearchResultItem[]>([]);
  const [pickerLoading, setPickerLoading] = useState(false);
  const [pickerActiveIndex, setPickerActiveIndex] = useState(0);

  useEffect(() => {
    if (!pickerOpen || !workspaceId) return;
    const q = pickerQuery.trim();
    if (!q) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      setPickerLoading(true);
      try {
        const res = await searchWorkspace(workspaceId, q);
        if (!cancelled) {
          setPickerResults(res.results.slice(0, 12));
          setPickerActiveIndex(0);
        }
      } catch {
        if (!cancelled) setPickerResults([]);
      } finally {
        if (!cancelled) setPickerLoading(false);
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [pickerOpen, pickerQuery, workspaceId]);

  const insertPageLink = useCallback(
    (result: SearchResultItem) => {
      if (!workspaceId) return;
      editor.createLink(`/w/${workspaceId}/pages/${result.page_id}`, result.title);
      setPickerOpen(false);
      setPickerQuery("");
      setPickerResults([]);
    },
    [editor, workspaceId],
  );

  const openPagePicker = useCallback(() => {
    setPickerQuery("");
    setPickerResults([]);
    setPickerActiveIndex(0);
    setPickerOpen(true);
  }, []);

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
          ref={titleInputRef}
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

          {/* Slash menu — default items + callout + page link */}
          <SuggestionMenuController
            triggerCharacter="/"
            getItems={async (query) =>
              filterSuggestionItems(
                [
                  ...getDefaultReactSlashMenuItems(editor),
                  calloutSlashMenuItem(editor),
                  pageLinkSlashMenuItem(editor, openPagePicker),
                ],
                query,
              )
            }
          />

          {/* @-mention suggestion menu for workspace members */}
          <SuggestionMenuController
            triggerCharacter="@"
            getItems={getMemberItems}
          />
        </BlockNoteView>
      </div>

      {/* Page picker (opened via /page slash item) */}
      <Dialog open={pickerOpen} onOpenChange={setPickerOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Link to a page</DialogTitle>
          </DialogHeader>
          <Input
            autoFocus
            value={pickerQuery}
            placeholder="Search pages…"
            onChange={(e) => {
              const v = e.target.value;
              setPickerQuery(v);
              if (!v.trim()) {
                setPickerResults([]);
                setPickerActiveIndex(0);
              }
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setPickerActiveIndex((i) => Math.min(i + 1, pickerResults.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setPickerActiveIndex((i) => Math.max(i - 1, 0));
              } else if (e.key === "Enter" && pickerResults[pickerActiveIndex]) {
                e.preventDefault();
                insertPageLink(pickerResults[pickerActiveIndex]);
              }
            }}
          />
          <div className="max-h-72 overflow-y-auto">
            {pickerLoading && (
              <p className="px-1 py-2 text-xs text-muted-foreground">Searching…</p>
            )}
            {!pickerLoading && pickerQuery.trim() && pickerResults.length === 0 && (
              <p className="px-1 py-2 text-xs text-muted-foreground">No pages match.</p>
            )}
            {!pickerQuery.trim() && (
              <p className="px-1 py-2 text-xs text-muted-foreground">
                Start typing to search pages in this workspace.
              </p>
            )}
            <ul className="flex flex-col gap-1">
              {pickerResults.map((r, i) => (
                <li key={r.page_id}>
                  <button
                    type="button"
                    onClick={() => insertPageLink(r)}
                    onMouseEnter={() => setPickerActiveIndex(i)}
                    className={`w-full rounded-md px-3 py-2 text-left transition-colors ${
                      i === pickerActiveIndex ? "bg-accent" : "hover:bg-accent/60"
                    }`}
                  >
                    <div className="text-sm font-medium text-foreground">{r.title}</div>
                    <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                      {r.space_name} / {r.collection_name}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </DialogContent>
      </Dialog>

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
