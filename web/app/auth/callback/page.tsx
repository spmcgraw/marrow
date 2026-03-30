"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getAuthStatus } from "@/lib/api";

export default function AuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    getAuthStatus()
      .then((status) => {
        if (status.authenticated) {
          router.replace("/workspaces");
        } else {
          router.replace("/login");
        }
      })
      .catch(() => {
        router.replace("/login");
      });
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground text-sm">Signing in...</p>
    </div>
  );
}
