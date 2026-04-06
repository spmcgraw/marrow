"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  getOrg,
  listOrgMembers,
  inviteMember,
  updateMemberRole,
  removeMember,
} from "@/lib/api";
import type { Organization, OrgMembership } from "@/lib/types";

const ROLES = ["owner", "editor", "viewer"] as const;

export default function OrgSettingsPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const [org, setOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrgMembership[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<string>("editor");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const [o, m] = await Promise.all([getOrg(orgId), listOrgMembers(orgId)]);
      setOrg(o);
      setMembers(m);
    } catch (err) {
      toast.error(String(err));
    }
  }

  useEffect(() => {
    load();
  }, [orgId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setBusy(true);
    try {
      await inviteMember(orgId, inviteEmail.trim(), inviteRole);
      setInviteEmail("");
      await load();
      toast.success("Member invited");
    } catch (err) {
      toast.error(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleRoleChange(membershipId: string, newRole: string) {
    try {
      await updateMemberRole(orgId, membershipId, newRole);
      await load();
    } catch (err) {
      toast.error(String(err));
    }
  }

  async function handleRemove(membershipId: string) {
    try {
      await removeMember(orgId, membershipId);
      await load();
    } catch (err) {
      toast.error(String(err));
    }
  }

  if (!org) {
    return <div className="p-8 text-muted-foreground">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-2xl p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">{org.name}</h1>
        <p className="text-sm text-muted-foreground">Organization settings</p>
      </div>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Members</h2>
        <div className="divide-y rounded-md border">
          {members.map((m) => (
            <div key={m.id} className="flex items-center justify-between px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">
                  {m.email}
                  {m.user_id === null && (
                    <span className="ml-2 text-xs text-amber-600">(pending)</span>
                  )}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={m.role}
                  onChange={(e) => handleRoleChange(m.id, e.target.value)}
                  className="text-sm border rounded px-2 py-1 bg-background"
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                <Button
                  variant="ghost"
                  size="xs"
                  onClick={() => handleRemove(m.id)}
                  className="text-destructive hover:text-destructive"
                >
                  Remove
                </Button>
              </div>
            </div>
          ))}
          {members.length === 0 && (
            <p className="px-4 py-3 text-sm text-muted-foreground">No members</p>
          )}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Invite member</h2>
        <form onSubmit={handleInvite} className="flex gap-2">
          <Input
            type="email"
            placeholder="Email address"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            disabled={busy}
            className="flex-1"
          />
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value)}
            className="text-sm border rounded px-2 py-1 bg-background"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <Button type="submit" disabled={busy || !inviteEmail.trim()}>
            Invite
          </Button>
        </form>
        <p className="text-xs text-muted-foreground">
          If the user hasn&apos;t signed up yet, the invite will be pending until they log in.
        </p>
      </section>
    </div>
  );
}
