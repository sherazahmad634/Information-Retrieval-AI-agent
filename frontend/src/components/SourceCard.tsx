"use client";

import { FileText } from "lucide-react";

import type { Citation } from "@/lib/types";

interface SourceCardProps {
  index: number;
  citation: Citation;
}

export function SourceCard({ index, citation }: SourceCardProps) {
  return (
    <div className="rounded-lg border border-ink-200 bg-ink-50 px-3 py-2 text-xs leading-relaxed text-ink-700 dark:border-ink-700 dark:bg-ink-900/40 dark:text-ink-100">
      <div className="mb-1 flex items-center justify-between gap-2 text-[11px] text-ink-500">
        <span className="inline-flex items-center gap-1">
          <FileText className="h-3 w-3" />
          <span className="font-mono">[{index}]</span>
          <span className="font-medium text-ink-700 dark:text-ink-100">
            {citation.document_title}
          </span>
          <span>· chunk {citation.position}</span>
        </span>
        <span className="font-mono">
          {citation.source} · {citation.score.toFixed(3)}
        </span>
      </div>
      <p className="line-clamp-6 whitespace-pre-wrap">{citation.text}</p>
    </div>
  );
}
