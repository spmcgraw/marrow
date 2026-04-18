/**
 * Marrow API client.
 *
 * All requests go through `apiFetch`, which attaches the API key header
 * and throws a descriptive error on non-2xx responses.
 */

import type {
  Attachment,
  AuthStatus,
  Collection,
  Organization,
  OrgMembership,
  Page,
  Revision,
  SearchResponse,
  Space,
  Workspace,
  WorkspaceTree,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    ...(options.headers as Record<string, string>),
  };

  // Server-side: forward the session cookie from the incoming request
  if (typeof window === "undefined") {
    const { cookies } = await import("next/headers");
    const cookieStore = await cookies();
    const session = cookieStore.get("marrow_session");
    if (session) {
      headers["Cookie"] = `marrow_session=${session.value}`;
    }
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include", // send cookies for cross-origin OIDC auth
    cache: "no-store", // always fetch fresh data — this is a wiki, not a CDN
  });

  if (!res.ok) {
    // Client-side 401: redirect to OIDC login
    if (res.status === 401 && typeof window !== "undefined") {
      window.location.href = `${BASE_URL}/api/auth/login`;
      return new Promise(() => {}); // page is navigating away
    }
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${text}`);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json();
}

// ---------------------------------------------------------------------------
// Workspaces
// ---------------------------------------------------------------------------

export function listWorkspaces(): Promise<Workspace[]> {
  return apiFetch("/api/workspaces");
}

export function createWorkspace(slug: string, name: string): Promise<Workspace> {
  return apiFetch("/api/workspaces", {
    method: "POST",
    body: JSON.stringify({ slug, name }),
  });
}

export function getWorkspace(id: string): Promise<Workspace> {
  return apiFetch(`/api/workspaces/${id}`);
}

export function getWorkspaceTree(id: string): Promise<WorkspaceTree> {
  return apiFetch(`/api/workspaces/${id}/tree`);
}

export function getExportSizeEstimate(
  workspaceId: string
): Promise<{ full_bytes: number; slim_bytes: number }> {
  return apiFetch(`/api/workspaces/${workspaceId}/export/estimate`);
}

export function exportWorkspaceUrl(workspaceId: string, slim: boolean): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const params = slim ? "?slim=true" : "";
  return `${base}/api/workspaces/${workspaceId}/export${params}`;
}

export async function restoreWorkspace(file: File): Promise<Workspace> {
  const form = new FormData();
  form.append("bundle", file);

  const headers: Record<string, string> = API_KEY ? { "X-API-Key": API_KEY } : {};

  const res = await fetch(`${BASE_URL}/api/workspaces/restore`, {
    method: "POST",
    body: form,
    headers,
    credentials: "include",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    let detail = text;
    try {
      detail = JSON.parse(text).detail ?? text;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

export function searchWorkspace(workspaceId: string, query: string): Promise<SearchResponse> {
  return apiFetch(`/api/workspaces/${workspaceId}/search?q=${encodeURIComponent(query)}`);
}

// ---------------------------------------------------------------------------
// Spaces
// ---------------------------------------------------------------------------

export function createSpace(workspaceId: string, slug: string, name: string): Promise<Space> {
  return apiFetch(`/api/workspaces/${workspaceId}/spaces`, {
    method: "POST",
    body: JSON.stringify({ slug, name }),
  });
}

// ---------------------------------------------------------------------------
// Collections
// ---------------------------------------------------------------------------

export function createCollection(spaceId: string, slug: string, name: string): Promise<Collection> {
  return apiFetch(`/api/spaces/${spaceId}/collections`, {
    method: "POST",
    body: JSON.stringify({ slug, name }),
  });
}

// ---------------------------------------------------------------------------
// Pages
// ---------------------------------------------------------------------------

export function createPage(
  collectionId: string,
  slug: string,
  title: string,
  content = "",
  content_format = "markdown"
): Promise<Page> {
  return apiFetch(`/api/collections/${collectionId}/pages`, {
    method: "POST",
    body: JSON.stringify({ slug, title, content, content_format }),
  });
}

export function getPage(pageId: string): Promise<Page> {
  return apiFetch(`/api/pages/${pageId}`);
}

export function updatePage(
  pageId: string,
  patch: { title?: string; content?: string; content_format?: string }
): Promise<Page> {
  return apiFetch(`/api/pages/${pageId}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deletePage(collectionId: string, pageId: string): Promise<void> {
  return apiFetch(`/api/collections/${collectionId}/pages/${pageId}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Revisions
// ---------------------------------------------------------------------------

export function listRevisions(pageId: string): Promise<Revision[]> {
  return apiFetch(`/api/pages/${pageId}/revisions`);
}

export function getRevision(pageId: string, revisionId: string): Promise<Revision> {
  return apiFetch(`/api/pages/${pageId}/revisions/${revisionId}`);
}

// ---------------------------------------------------------------------------
// Attachments
// ---------------------------------------------------------------------------

export function listAttachments(collectionId: string, pageId: string): Promise<Attachment[]> {
  return apiFetch(`/api/collections/${collectionId}/pages/${pageId}/attachments`);
}

export async function uploadAttachment(
  collectionId: string,
  pageId: string,
  file: File
): Promise<Attachment> {
  const form = new FormData();
  form.append("file", file);

  const headers: Record<string, string> = API_KEY ? { "X-API-Key": API_KEY } : {};

  const res = await fetch(
    `${BASE_URL}/api/collections/${collectionId}/pages/${pageId}/attachments`,
    { method: "POST", body: form, headers, credentials: "include" }
  );

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Upload error ${res.status}: ${text}`);
  }
  return res.json();
}

export function attachmentFileUrl(collectionId: string, pageId: string, attachmentId: string): string {
  return `${BASE_URL}/api/collections/${collectionId}/pages/${pageId}/attachments/${attachmentId}/file`;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export function getAuthStatus(): Promise<AuthStatus> {
  return apiFetch("/api/auth/me");
}

export async function logout(): Promise<string | null> {
  const data = await apiFetch<{ status: string; logout_url?: string }>("/api/auth/logout", {
    method: "POST",
  });
  return data.logout_url ?? null;
}

// ---------------------------------------------------------------------------
// Organizations
// ---------------------------------------------------------------------------

export function listOrgs(): Promise<Organization[]> {
  return apiFetch("/api/orgs");
}

export function createOrg(slug: string, name: string): Promise<Organization> {
  return apiFetch("/api/orgs", {
    method: "POST",
    body: JSON.stringify({ slug, name }),
  });
}

export function getOrg(orgId: string): Promise<Organization> {
  return apiFetch(`/api/orgs/${orgId}`);
}

export function listOrgMembers(orgId: string): Promise<OrgMembership[]> {
  return apiFetch(`/api/orgs/${orgId}/members`);
}

export function inviteMember(
  orgId: string,
  email: string,
  role: string
): Promise<OrgMembership> {
  return apiFetch(`/api/orgs/${orgId}/members`, {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });
}

export function updateMemberRole(
  orgId: string,
  membershipId: string,
  role: string
): Promise<OrgMembership> {
  return apiFetch(`/api/orgs/${orgId}/members/${membershipId}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export function removeMember(orgId: string, membershipId: string): Promise<void> {
  return apiFetch(`/api/orgs/${orgId}/members/${membershipId}`, {
    method: "DELETE",
  });
}

/** Convert a display name to a URL-safe slug. */
export function slugify(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}
