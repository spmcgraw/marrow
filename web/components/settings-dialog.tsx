"use client";

import { useState } from "react";
import { Settings } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface Props {
  trigger?: React.ReactNode;
}

export function SettingsDialog({ trigger }: Props) {
  const [open, setOpen] = useState(false);

  const triggerContent = trigger ?? (
    <>
      <Settings className="h-3.5 w-3.5" />
      <span className="sr-only">Settings</span>
    </>
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <button
            type="button"
            title="Settings"
            className="flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground"
          />
        }
      >
        {triggerContent}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>Personal preferences for this account.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <section className="flex items-center justify-between rounded-md border border-border px-3 py-2.5">
            <div>
              <div className="text-sm font-medium">Appearance</div>
              <div className="text-xs text-muted-foreground">Toggle dark or light mode.</div>
            </div>
            <ThemeToggle />
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
