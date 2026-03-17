import { getPage } from "@/lib/api";
import { PageEditor } from "@/components/page-editor";

interface Props {
  params: Promise<{ workspaceId: string; pageId: string }>;
}

export default async function PageRoute({ params }: Props) {
  const { pageId } = await params;
  const page = await getPage(pageId);

  return <PageEditor initialPage={page} />;
}
