"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ChevronDown, ChevronRight, FilePlus, FolderPlus, Plus, Settings } from "lucide-react";
import { ExportDialog } from "@/components/export-dialog";
import { ThemeToggle } from "@/components/theme-toggle";
import { toast } from "sonner";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createCollection, createPage, createSpace, logout, slugify } from "@/lib/api";
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

function CreateDialog({
  trigger,
  title,
  placeholder,
  onSubmit,
}: {
  trigger: React.ReactNode;
  title: string;
  placeholder: string;
  onSubmit: (name: string) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!value.trim()) return;
    setBusy(true);
    try {
      await onSubmit(value.trim());
      setValue("");
      setOpen(false);
    } catch (err) {
      toast.error(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<button type="button" className="contents" />}>
        {trigger}
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <Input
            placeholder={placeholder}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            autoFocus
            disabled={busy}
          />
          <DialogFooter>
            <Button type="submit" disabled={busy || !value.trim()}>
              Create
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
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
  const router = useRouter();

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
        <CreateDialog
          trigger={
            <span className="hidden group-hover:flex items-center text-muted-foreground hover:text-foreground cursor-pointer" title="New page">
              <FilePlus className="h-3 w-3" />
            </span>
          }
          title="New Page"
          placeholder="Page title"
          onSubmit={async (name) => {
            const page = await createPage(col.id, slugify(name), name);
            onCreated();
            router.push(`/w/${workspaceId}/pages/${page.id}`);
          }}
        />
      </div>
      {open && (
        <SidebarMenu>
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
          {col.pages.length === 0 && (
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
        <CreateDialog
          trigger={
            <span className="mr-2 hidden group-hover:flex items-center text-muted-foreground hover:text-foreground cursor-pointer" title="New collection">
              <FolderPlus className="h-3.5 w-3.5" />
            </span>
          }
          title="New Collection"
          placeholder="Collection name"
          onSubmit={async (name) => {
            await createCollection(space.id, slugify(name), name);
            onCreated();
          }}
        />
      </div>
      {open && (
        <SidebarGroupContent>
          {space.collections.map((col) => (
            <CollectionSection
              key={col.id}
              col={col}
              workspaceId={workspaceId}
              activePath={activePath}
              onCreated={onCreated}
            />
          ))}
          {space.collections.length === 0 && (
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
  return (
    <div className="min-h-0 flex-1 overflow-y-auto py-1">
      <div className="flex items-center justify-between px-3 py-1 group">
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
          Spaces
        </span>
        <CreateDialog
          trigger={
            <span className="opacity-0 group-hover:opacity-100 cursor-pointer text-muted-foreground hover:text-foreground" title="New space">
              <Plus className="h-3.5 w-3.5" />
            </span>
          }
          title="New Space"
          placeholder="Space name"
          onSubmit={async (name) => {
            await createSpace(tree.id, slugify(name), name);
            refresh();
          }}
        />
      </div>
      {tree.spaces.map((space) => (
        <SpaceSection
          key={space.id}
          space={space}
          workspaceId={tree.id}
          activePath={activePath}
          onCreated={refresh}
        />
      ))}
      {tree.spaces.length === 0 && (
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

export function AppSidebar({ tree, user, panel, memberCount, searchInputRef }: Props) {
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

      {user && (
        <div className="flex items-center justify-between gap-2 border-t border-sidebar-border px-3 py-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-foreground">{user.name}</p>
            <p className="truncate text-xs text-muted-foreground">{user.email}</p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <ThemeToggle />
            <Button
              variant="ghost"
              size="xs"
              onClick={async () => {
                const logoutUrl = await logout();
                window.location.href = logoutUrl ?? "/login";
              }}
            >
              Sign out
            </Button>
          </div>
        </div>
      )}
    </aside>
  );
}
