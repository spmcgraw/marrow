"use client";

import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

const subscribe = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  // Avoid SSR hydration mismatch on the icon: render a placeholder on the
  // server snapshot, the real toggle on the client snapshot.
  const mounted = useSyncExternalStore(subscribe, getClientSnapshot, getServerSnapshot);

  if (!mounted) return <div className="h-7 w-7" />;

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      title={resolvedTheme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      className="h-7 w-7 p-0"
    >
      {resolvedTheme === "dark" ? (
        <Sun className="h-3.5 w-3.5" />
      ) : (
        <Moon className="h-3.5 w-3.5" />
      )}
    </Button>
  );
}
