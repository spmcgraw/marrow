"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createWorkspace, listWorkspaces, slugify } from "@/lib/api";
import type { Workspace } from "@/lib/types";

export default function WorkspacesPage() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    listWorkspaces().then(setWorkspaces).catch(() => toast.error("Failed to load workspaces"));
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
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Freehold</h1>
          <p className="text-sm text-muted-foreground">Your knowledge, owned outright.</p>
        </div>

        {workspaces.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Workspaces
            </p>
            {workspaces.map((ws) => (
              <Link
                key={ws.id}
                href={`/w/${ws.id}`}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm hover:bg-accent"
              >
                <span className="font-medium">{ws.name}</span>
                <span className="text-xs text-muted-foreground">{ws.slug}</span>
              </Link>
            ))}
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
      </div>
    </div>
  );
}
