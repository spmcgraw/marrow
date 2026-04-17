"use client";

import { ChevronRight } from "lucide-react";
import { useWorkspaceTree, findBreadcrumb } from "@/components/workspace-tree-context";

export function PageBreadcrumbs({ collectionId }: { collectionId: string }) {
  const tree = useWorkspaceTree();
  if (!tree) return null;

  const crumb = findBreadcrumb(tree, collectionId);
  if (!crumb) return null;

  return (
    <nav className="flex items-center gap-1 text-xs text-muted-foreground">
      <span>{crumb.spaceName}</span>
      <ChevronRight className="h-3 w-3" />
      <span>{crumb.collectionName}</span>
    </nav>
  );
}
