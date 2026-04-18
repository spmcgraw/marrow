// TypeScript types mirroring the Marrow API Pydantic schemas.

export interface Organization {
  id: string;
  slug: string;
  name: string;
  created_at: string;
}

export interface OrgMembership {
  id: string;
  org_id: string;
  user_id: string | null;
  email: string;
  role: "owner" | "editor" | "viewer";
  created_at: string;
}

export interface Workspace {
  id: string;
  org_id: string;
  slug: string;
  name: string;
  created_at: string;
}

export interface Space {
  id: string;
  workspace_id: string;
  slug: string;
  name: string;
  created_at: string;
}

export interface Collection {
  id: string;
  space_id: string;
  slug: string;
  name: string;
  created_at: string;
}

export interface Page {
  id: string;
  collection_id: string;
  slug: string;
  title: string;
  current_revision_id: string | null;
  created_at: string;
  content?: string | null;
  content_format?: string; // 'markdown' | 'json'
}

export interface Revision {
  id: string;
  page_id: string;
  content_format: string; // 'markdown' | 'json'
  created_at: string;
  content?: string;
}

export interface Attachment {
  id: string;
  page_id: string;
  filename: string;
  hash: string;
  size_bytes: number;
  created_at: string;
}

// Search
export interface SearchResultItem {
  page_id: string;
  title: string;
  snippet: string;
  collection_id: string;
  space_id: string;
  space_name: string;
  collection_name: string;
  rank: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResultItem[];
}

// Nested tree for sidebar rendering
export interface PageTreeItem {
  id: string;
  collection_id: string;
  slug: string;
  title: string;
  current_revision_id: string | null;
}

export interface CollectionTreeItem {
  id: string;
  slug: string;
  name: string;
  pages: PageTreeItem[];
}

export interface SpaceTreeItem {
  id: string;
  slug: string;
  name: string;
  collections: CollectionTreeItem[];
}

export interface WorkspaceTree {
  id: string;
  org_id: string;
  slug: string;
  name: string;
  spaces: SpaceTreeItem[];
}

// Auth
export interface User {
  id: string;
  email: string;
  name: string;
}

export interface AuthStatus {
  authenticated: boolean;
  user: User | null;
  method: string;
  oidc_enabled: boolean;
}
