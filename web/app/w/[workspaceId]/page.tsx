import { BookOpen } from "lucide-react";

export default function WorkspaceHomePage() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <BookOpen className="h-12 w-12 text-muted-foreground/50" />
      <div className="space-y-1">
        <h2 className="font-heading text-lg font-semibold">Welcome to your workspace</h2>
        <p className="max-w-sm text-sm text-muted-foreground">
          Organize your knowledge into spaces, collections, and pages.
          Select a page from the sidebar, or create a space to get started.
        </p>
      </div>
    </div>
  );
}
