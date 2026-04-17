"use client";

import { createContext, useContext } from "react";
import type { WorkspaceTree } from "@/lib/types";

const WorkspaceTreeContext = createContext<WorkspaceTree | null>(null);

export function WorkspaceTreeProvider({
  tree,
  children,
}: {
  tree: WorkspaceTree;
  children: React.ReactNode;
}) {
  return <WorkspaceTreeContext value={tree}>{children}</WorkspaceTreeContext>;
}

export function useWorkspaceTree() {
  return useContext(WorkspaceTreeContext);
}

export function findBreadcrumb(tree: WorkspaceTree, collectionId: string) {
  for (const space of tree.spaces) {
    for (const col of space.collections) {
      if (col.id === collectionId) {
        return { spaceName: space.name, collectionName: col.name };
      }
    }
  }
  return null;
}
