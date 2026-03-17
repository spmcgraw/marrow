import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { getWorkspaceTree } from "@/lib/api";

interface Props {
  children: React.ReactNode;
  params: Promise<{ workspaceId: string }>;
}

export default async function WorkspaceLayout({ children, params }: Props) {
  const { workspaceId } = await params;

  // Fetch the full tree server-side so the sidebar has all data on first paint.
  const tree = await getWorkspaceTree(workspaceId);

  return (
    <SidebarProvider>
      <AppSidebar tree={tree} />
      <SidebarInset>{children}</SidebarInset>
    </SidebarProvider>
  );
}
