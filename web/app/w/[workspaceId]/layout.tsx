import { redirect } from "next/navigation";
import { WorkspaceShell } from "@/components/workspace-shell";
import { getAuthStatus, getWorkspaceTree, listOrgMembers } from "@/lib/api";

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
  const members = await listOrgMembers(tree.org_id).catch(() => null);
  const memberCount = members ? members.length : null;

  return (
    <WorkspaceShell tree={tree} user={auth?.user ?? null} memberCount={memberCount}>
      {children}
    </WorkspaceShell>
  );
}
