"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ChevronDown, ChevronRight, FilePlus, FolderPlus, Plus, Settings } from "lucide-react";
import { ExportDialog } from "@/components/export-dialog";
import { ThemeToggle } from "@/components/theme-toggle";
import { toast } from "sonner";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
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
import { SearchDialog } from "@/components/search-dialog";
import type { CollectionTreeItem, SpaceTreeItem, User, WorkspaceTree } from "@/lib/types";

interface Props {
  tree: WorkspaceTree;
  user?: User | null;
}

// Simple modal form used for Space, Collection, and Page creation.
// Uses plain buttons as triggers since shadcn v4 (Base UI) uses the `render` prop
// pattern rather than `asChild` for composing triggers.
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
      {/* Wrap the custom trigger in DialogTrigger without asChild — Base UI renders it correctly */}
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
                {/* Base UI render prop: pass the <a> as the rendered element */}
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

export function AppSidebar({ tree, user }: Props) {
  const pathname = usePathname();
  const router = useRouter();

  function refresh() {
    router.refresh();
  }

  return (
    <Sidebar>
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="flex items-center justify-between px-2 py-1.5">
          <a href="/workspaces" className="text-sm font-semibold tracking-tight hover:opacity-70">
            Freehold
          </a>
          <SidebarTrigger className="-mr-1" />
        </div>
        <div className="flex items-center justify-between px-2 pb-1.5 group">
          <span className="text-xs font-medium text-muted-foreground">{tree.name}</span>
          <div className="flex items-center gap-1">
            <ExportDialog workspaceId={tree.id} workspaceName={tree.name} />
            <a
              href={`/orgs/${tree.org_id}/settings`}
              className="hidden group-hover:flex items-center text-muted-foreground hover:text-foreground"
              title="Organization settings"
            >
              <Settings className="h-3.5 w-3.5" />
            </a>
          <CreateDialog
            trigger={
              <span className="hidden group-hover:flex items-center text-muted-foreground hover:text-foreground cursor-pointer" title="New space">
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
        </div>
        <div className="px-2 pb-2">
          <SearchDialog workspaceId={tree.id} />
        </div>
      </SidebarHeader>

      <SidebarContent>
        {tree.spaces.map((space) => (
          <SpaceSection
            key={space.id}
            space={space}
            workspaceId={tree.id}
            activePath={pathname}
            onCreated={refresh}
          />
        ))}
        {tree.spaces.length === 0 && (
          <div className="px-4 py-6 text-center">
            <p className="text-xs text-muted-foreground">
              No spaces yet
            </p>
            <p className="mt-1 text-xs text-muted-foreground/70">
              Hover the workspace name above and click <strong>+</strong> to create one.
            </p>
          </div>
        )}
      </SidebarContent>

      {user && (
        <SidebarFooter className="border-t border-sidebar-border">
          <div className="flex items-center justify-between px-2 py-1.5">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{user.name}</p>
              <p className="truncate text-xs text-muted-foreground">{user.email}</p>
            </div>
            <div className="flex items-center gap-1">
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
        </SidebarFooter>
      )}
    </Sidebar>
  );
}
