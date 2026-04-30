import { redirect } from "next/navigation";
import { getApiUrl, getOidcEnabled } from "@/lib/runtime-config";

export default function LoginPage() {
  if (!getOidcEnabled()) {
    redirect("/workspaces");
  }

  const apiUrl = getApiUrl();

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-sm space-y-6 text-center">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold tracking-tight">Marrow</h1>
          <p className="text-muted-foreground text-sm">
            Sign in to access your workspace
          </p>
        </div>
        <a
          href={`${apiUrl}/api/auth/login`}
          className="inline-flex h-9 w-full items-center justify-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          Sign in with SSO
        </a>
      </div>
    </div>
  );
}
