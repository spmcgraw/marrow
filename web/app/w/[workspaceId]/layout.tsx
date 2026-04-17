import { redirect } from "next/navigation";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { InsetHeader } from "@/components/inset-header";
import { WorkspaceTreeProvider } from "@/components/workspace-tree-context";
import { getAuthStatus, getWorkspaceTree } from "@/lib/api";

interface Props {
  children: React.ReactNode;
  params: Promise<{ workspaceId: string }>;
}

export default async function WorkspaceLayout({ children, params }: Props) {
  const { workspaceId } = await params;

  let tree;
  try {
    tree = await getWorkspaceTree(workspaceId);
  } catch (e: unknown) {
    if (e instanceof Error && e.message.includes("401")) {
      redirect("/login");
    }
    throw e;
  }

  const auth = await getAuthStatus().catch(() => null);

  return (
    <SidebarProvider>
      <AppSidebar tree={tree} user={auth?.user ?? null} />
      <SidebarInset>
        <InsetHeader />
        <WorkspaceTreeProvider tree={tree}>{children}</WorkspaceTreeProvider>
      </SidebarInset>
    </SidebarProvider>
  );
}
