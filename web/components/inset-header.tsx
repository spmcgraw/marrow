"use client";

import { SidebarTrigger, useSidebar } from "@/components/ui/sidebar";

export function InsetHeader() {
  const { open, isMobile } = useSidebar();

  // Show trigger when sidebar is collapsed on desktop, or always on mobile
  if (open && !isMobile) return null;

  return (
    <header className="flex h-10 items-center border-b px-4">
      <SidebarTrigger />
    </header>
  );
}
