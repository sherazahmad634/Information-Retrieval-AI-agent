"use client";

import { FileText, Trash2 } from "lucide-react";

import type { DocumentSummary } from "@/lib/types";

interface DocumentListProps {
  documents: DocumentSummary[];
  loading: boolean;
  onDelete: (id: string) => Promise<void>;
}

export function DocumentList({ documents, loading, onDelete }: DocumentListProps) {
  if (loading) {
    return <p className="text-xs text-ink-500">Loading documents…</p>;
  }
  if (documents.length === 0) {
    return (
      <p className="text-xs text-ink-500">
        No documents yet. Upload one or seed the corpus.
      </p>
    );
  }
  return (
    <ul className="space-y-1.5">
      {documents.map((d) => (
        <li
          key={d.id}
          className="group flex items-start justify-between gap-2 rounded-md border border-transparent px-2 py-1.5 text-xs hover:border-ink-200 hover:bg-ink-100 dark:hover:bg-ink-700/30"
        >
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-1.5 truncate font-medium text-ink-900 dark:text-ink-50">
              <FileText className="h-3 w-3 shrink-0" />
              {d.title}
            </p>
            <p className="text-[11px] text-ink-500">
              {d.chunk_count} chunks · {d.char_count.toLocaleString()} chars
            </p>
          </div>
          <button
            type="button"
            onClick={() => void onDelete(d.id)}
            className="invisible shrink-0 rounded p-1 text-ink-500 hover:bg-red-100 hover:text-red-600 group-hover:visible dark:hover:bg-red-900/20"
            aria-label={`Delete ${d.title}`}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </li>
      ))}
    </ul>
  );
}
