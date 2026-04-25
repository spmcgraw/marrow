"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ChevronDown, ChevronRight, FilePlus, FolderPlus, Plus, Settings } from "lucide-react";
import { ExportDialog } from "@/components/export-dialog";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { InlineCreateRow } from "@/components/sidebar/inline-create-row";
import { createCollection, createPage, createSpace, slugify } from "@/lib/api";
import { SearchPanel } from "@/components/rail-panels/search-panel";
import { StarredPanel } from "@/components/rail-panels/starred-panel";
import { InboxPanel } from "@/components/rail-panels/inbox-panel";
import type { RailPanel } from "@/components/app-rail";
import type { CollectionTreeItem, SpaceTreeItem, User, WorkspaceTree } from "@/lib/types";

interface Props {
  tree: WorkspaceTree;
  user?: User | null;
  panel: RailPanel;
  memberCount: number | null;
  searchInputRef: React.RefObject<HTMLInputElement | null>;
}

function CollectionSection({
  col,
  workspaceId,
  activePath,
  onCreated,
}: {
  col: CollectionTreeItem;
  workspaceId: string;
  activePath: string;
  onCreated: () => void;
}) {
  const [open, setOpen] = useState(true);
  const [creating, setCreating] = useState(false);
  const router = useRouter();

  function startCreate() {
    setOpen(true);
    setCreating(true);
  }

  return (
    <div className="ml-3">
      <div className="flex items-center justify-between py-0.5 group">
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex flex-1 items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          {col.name}
        </button>
        <button
          type="button"
          onClick={startCreate}
          className="hidden group-hover:flex items-center text-muted-foreground hover:text-foreground"
          title="New page"
          aria-label="New page"
        >
          <FilePlus className="h-3 w-3" />
        </button>
      </div>
      {open && (
        <SidebarMenu>
          {creating && (
            <InlineCreateRow
              placeholder="Page title"
              className="flex items-center gap-2 px-2 py-1"
              icon={<FilePlus className="h-3 w-3 text-muted-foreground" />}
              onCommit={async (name) => {
                const page = await createPage(col.id, slugify(name), name);
                setCreating(false);
                router.push(`/w/${workspaceId}/pages/${page.id}?new=1`);
                onCreated();
              }}
              onCancel={() => setCreating(false)}
            />
          )}
          {col.pages.map((page) => {
            const href = `/w/${workspaceId}/pages/${page.id}`;
            const isActive = activePath === href;
            return (
              <SidebarMenuItem key={page.id}>
                <SidebarMenuButton
                  render={<a href={href} />}
                  isActive={isActive}
                  size="sm"
                >
                  {page.title}
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
          {!creating && col.pages.length === 0 && (
            <p className="px-2 py-1 text-xs text-muted-foreground">No pages yet</p>
          )}
        </SidebarMenu>
      )}
    </div>
  );
}

function SpaceSection({
  space,
  workspaceId,
  activePath,
  onCreated,
}: {
  space: SpaceTreeItem;
  workspaceId: string;
  activePath: string;
  onCreated: () => void;
}) {
  const [open, setOpen] = useState(true);
  const [creating, setCreating] = useState(false);

  function startCreate() {
    setOpen(true);
    setCreating(true);
  }

  return (
    <SidebarGroup>
      <div className="flex items-center justify-between group">
        <SidebarGroupLabel
          className="flex flex-1 cursor-pointer items-center gap-2"
          onClick={() => setOpen((o) => !o)}
        >
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-primary/10 text-[10px] font-semibold text-primary">
            {space.name[0]?.toUpperCase()}
          </span>
          {space.name}
        </SidebarGroupLabel>
        <button
          type="button"
          onClick={startCreate}
          className="mr-2 hidden group-hover:flex items-center text-muted-foreground hover:text-foreground"
          title="New collection"
          aria-label="New collection"
        >
          <FolderPlus className="h-3.5 w-3.5" />
        </button>
      </div>
      {open && (
        <SidebarGroupContent>
          {creating && (
            <InlineCreateRow
              placeholder="Collection name"
              className="ml-3 flex items-center gap-2 py-0.5"
              icon={<FolderPlus className="h-3 w-3 text-muted-foreground" />}
              onCommit={async (name) => {
                await createCollection(space.id, slugify(name), name);
                setCreating(false);
                onCreated();
              }}
              onCancel={() => setCreating(false)}
            />
          )}
          {space.collections.map((col) => (
            <CollectionSection
              key={col.id}
              col={col}
              workspaceId={workspaceId}
              activePath={activePath}
              onCreated={onCreated}
            />
          ))}
          {!creating && space.collections.length === 0 && (
            <p className="px-4 py-1 text-xs text-muted-foreground">No collections yet</p>
          )}
        </SidebarGroupContent>
      )}
    </SidebarGroup>
  );
}

function WorkspaceHeader({ tree, memberCount }: { tree: WorkspaceTree; memberCount: number | null }) {
  return (
    <div className="flex items-center gap-2 border-b border-sidebar-border px-3.5 py-3 group">
      <div className="min-w-0 flex-1">
        <div className="truncate text-[13.5px] font-medium text-foreground">{tree.name}</div>
        <div className="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">
          {memberCount !== null ? `${memberCount} member${memberCount === 1 ? "" : "s"}` : "workspace"}
        </div>
      </div>
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <ExportDialog workspaceId={tree.id} workspaceName={tree.name} />
        <a
          href={`/orgs/${tree.org_id}/settings`}
          className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground"
          title="Organization settings"
        >
          <Settings className="h-3.5 w-3.5" />
        </a>
      </div>
      <button
        type="button"
        className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground"
        title="Workspace menu"
        aria-label="Workspace menu"
      >
        <ChevronDown className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function PagesPanel({
  tree,
  activePath,
  refresh,
}: {
  tree: WorkspaceTree;
  activePath: string;
  refresh: () => void;
}) {
  const [creatingSpace, setCreatingSpace] = useState(false);

  return (
    <div className="min-h-0 flex-1 overflow-y-auto py-1">
      <div className="flex items-center justify-between px-3 py-1 group">
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
          Spaces
        </span>
        <button
          type="button"
          onClick={() => setCreatingSpace(true)}
          className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground"
          title="New space"
          aria-label="New space"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>
      {creatingSpace && (
        <InlineCreateRow
          placeholder="Space name"
          className="flex items-center gap-2 px-3 py-1"
          icon={
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-primary/10 text-[10px] font-semibold text-primary">
              ·
            </span>
          }
          onCommit={async (name) => {
            await createSpace(tree.id, slugify(name), name);
            setCreatingSpace(false);
            refresh();
          }}
          onCancel={() => setCreatingSpace(false)}
        />
      )}
      {tree.spaces.map((space) => (
        <SpaceSection
          key={space.id}
          space={space}
          workspaceId={tree.id}
          activePath={activePath}
          onCreated={refresh}
        />
      ))}
      {!creatingSpace && tree.spaces.length === 0 && (
        <div className="px-4 py-6 text-center">
          <p className="text-xs text-muted-foreground">No spaces yet</p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            Hover <strong>Spaces</strong> above and click <strong>+</strong> to create one.
          </p>
        </div>
      )}
    </div>
  );
}

export function AppSidebar({ tree, panel, memberCount, searchInputRef }: Props) {
  const pathname = usePathname();
  const router = useRouter();

  function refresh() {
    router.refresh();
  }

  return (
    <aside className="flex h-full w-[272px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <WorkspaceHeader tree={tree} memberCount={memberCount} />

      {panel === "pages" && <PagesPanel tree={tree} activePath={pathname} refresh={refresh} />}
      {panel === "search" && <SearchPanel workspaceId={tree.id} inputRef={searchInputRef} />}
      {panel === "starred" && <StarredPanel />}
      {panel === "inbox" && <InboxPanel />}
    </aside>
  );
}
