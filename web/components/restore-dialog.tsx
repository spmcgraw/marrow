"use client";

import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { restoreWorkspace } from "@/lib/api";

export function RestoreDialog() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFileChange(chosen: File | null) {
    setError(null);
    if (!chosen) return;
    if (!chosen.name.endsWith(".zip")) {
      setError("Only .zip bundle files are accepted.");
      return;
    }
    setFile(chosen);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0] ?? null;
    handleFileChange(dropped);
  }

  async function handleRestore() {
    if (!file) return;
    setRestoring(true);
    setError(null);
    try {
      const ws = await restoreWorkspace(file);
      toast.success(`Workspace "${ws.name}" restored successfully`);
      setOpen(false);
      router.push(`/w/${ws.id}`);
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/, ""));
    } finally {
      setRestoring(false);
    }
  }

  function handleOpenChange(isOpen: boolean) {
    if (!isOpen) {
      setFile(null);
      setError(null);
    }
    setOpen(isOpen);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={<button type="button" className="contents" />}>
        <Button variant="outline" type="button" className="w-full">
          <Upload className="h-3.5 w-3.5 mr-1.5" />
          Restore from bundle
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Restore workspace</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-1">
          <p className="text-sm text-muted-foreground">
            Upload a Freehold export bundle (.zip) to restore a workspace. Full and slim bundles are
            both supported.
          </p>

          <div
            className={`relative flex flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed px-4 py-6 text-center transition-colors cursor-pointer ${
              dragging
                ? "border-primary bg-primary/5"
                : "border-border hover:border-muted-foreground/50"
            }`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={(e) => {
              if (!e.currentTarget.contains(e.relatedTarget as Node)) {
                setDragging(false);
              }
            }}
            onDrop={handleDrop}
          >
            <Upload className="h-5 w-5 text-muted-foreground" />
            {file ? (
              <p className="text-sm font-medium">{file.name}</p>
            ) : (
              <p className="text-sm text-muted-foreground">
                Drop bundle here or <span className="text-foreground underline">browse</span>
              </p>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
            />
          </div>

          {error && (
            <p className="text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded px-2 py-1.5">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button onClick={handleRestore} disabled={!file || restoring}>
            {restoring ? "Restoring…" : "Restore"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
