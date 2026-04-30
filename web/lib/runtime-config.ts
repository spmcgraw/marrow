// Runtime config — read on every request so self-hosters can change env vars
// without rebuilding the web image.
//
// Server-side (SSR, server components, route handlers, middleware): values
// are read from process.env at request time. Standalone Next.js does not
// inline non-NEXT_PUBLIC_ env vars, so this works at runtime.
//
// Browser-side: values come from window.__MARROW_CONFIG__, which is populated
// by /config.js — a small script generated at container startup by
// docker-entrypoint.sh and loaded by app/layout.tsx before any client code.

export interface RuntimeConfig {
  apiUrl: string;
  apiKey: string;
  oidcEnabled: boolean;
}

declare global {
  interface Window {
    __MARROW_CONFIG__?: Partial<RuntimeConfig>;
  }
}

const DEFAULT_API_URL = "http://localhost:8000";

export function getApiUrl(): string {
  if (typeof window === "undefined") {
    return process.env.MARROW_API_URL || DEFAULT_API_URL;
  }
  return window.__MARROW_CONFIG__?.apiUrl || DEFAULT_API_URL;
}

export function getApiKey(): string {
  if (typeof window === "undefined") {
    return process.env.MARROW_API_KEY || "";
  }
  return window.__MARROW_CONFIG__?.apiKey || "";
}

export function getOidcEnabled(): boolean {
  if (typeof window === "undefined") {
    return process.env.MARROW_OIDC_ENABLED === "true";
  }
  return window.__MARROW_CONFIG__?.oidcEnabled === true;
}

export function getInternalApiUrl(): string {
  return process.env.INTERNAL_API_URL || getApiUrl();
}
