import { redirect } from "next/navigation";

// Root always redirects to the workspace list.
export default function Home() {
  redirect("/workspaces");
}
