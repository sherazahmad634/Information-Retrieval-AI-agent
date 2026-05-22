"use client";

import { Calculator, Database, Globe, NotebookPen, Search, Wrench } from "lucide-react";

import type { AgentTraceEvent } from "@/lib/types";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  document_search: Search,
  document_ingest: Database,
  web_search: Globe,
  calculator: Calculator,
  remember: NotebookPen,
  recall: NotebookPen,
};

interface ToolBadgeProps {
  trace: AgentTraceEvent;
}

export function ToolBadge({ trace }: ToolBadgeProps) {
  const Icon = ICONS[trace.tool] ?? Wrench;
  return (
    <span
      title={trace.summary}
      className="inline-flex items-center gap-1 rounded-full bg-ink-100 px-2 py-0.5 font-mono text-[11px] text-ink-700 dark:bg-ink-700/40 dark:text-ink-100"
    >
      <Icon className="h-3 w-3" />
      {trace.tool}
    </span>
  );
}
