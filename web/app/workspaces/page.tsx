"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Settings } from "lucide-react";
import { createWorkspace, getAuthStatus, listOrgs, listWorkspaces, logout, slugify } from "@/lib/api";
import type { AuthStatus, Organization, Workspace } from "@/lib/types";
import { RestoreDialog } from "@/components/restore-dialog";

export default function WorkspacesPage() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    listWorkspaces().then(setWorkspaces).catch(() => toast.error("Failed to load workspaces"));
    listOrgs().then(setOrgs).catch(() => {});
    getAuthStatus().then(setAuth).catch(() => {});
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      const ws = await createWorkspace(slugify(name), name.trim());
      router.push(`/w/${ws.id}`);
    } catch (err) {
      toast.error(String(err));
      setCreating(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-background px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Freehold</h1>
            <p className="text-sm text-muted-foreground">Your knowledge, owned outright.</p>
          </div>
          {auth?.authenticated && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>{auth.user?.name}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={async () => {
                  const logoutUrl = await logout();
                  window.location.href = logoutUrl ?? "/login";
                }}
              >
                Sign out
              </Button>
            </div>
          )}
        </div>

        {orgs.length > 0 && (
          <div className="space-y-4">
            {orgs.map((org) => {
              const orgWorkspaces = workspaces.filter((ws) => ws.org_id === org.id);
              return (
                <div key={org.id} className="space-y-1">
                  <div className="flex items-center justify-between group">
                    <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      {org.name}
                    </p>
                    <Link
                      href={`/orgs/${org.id}/settings`}
                      className="text-muted-foreground hover:text-foreground transition-colors opacity-0 group-hover:opacity-100"
                      title="Organization settings"
                    >
                      <Settings className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                  {orgWorkspaces.map((ws) => (
                    <Link
                      key={ws.id}
                      href={`/w/${ws.id}`}
                      className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm hover:bg-accent"
                    >
                      <span className="font-medium">{ws.name}</span>
                      <span className="text-xs text-muted-foreground">{ws.slug}</span>
                    </Link>
                  ))}
                  {orgWorkspaces.length === 0 && (
                    <p className="px-3 py-2 text-xs text-muted-foreground">No workspaces yet</p>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <form onSubmit={handleCreate} className="flex gap-2">
          <Input
            placeholder="New workspace name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={creating}
          />
          <Button type="submit" disabled={creating || !name.trim()}>
            Create
          </Button>
        </form>

        <RestoreDialog />
      </div>
    </div>
  );
}
