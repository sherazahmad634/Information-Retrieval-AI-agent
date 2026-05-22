"use client";

import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

interface DocumentUploadProps {
  onUpload: (file: File) => Promise<void>;
}

export function DocumentUpload({ onUpload }: DocumentUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File | undefined) => {
    if (!file) return;
    setError(null);
    setBusy(true);
    try {
      await onUpload(file);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={busy}
        className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-ink-300 bg-white px-3 py-3 text-xs text-ink-700 transition hover:border-accent-500 hover:text-accent-600 disabled:opacity-50 dark:border-ink-700 dark:bg-ink-900 dark:text-ink-100"
      >
        <UploadCloud className="h-4 w-4" />
        {busy ? "Uploading…" : "Upload document"}
      </button>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".txt,.md,.markdown,.html,.htm,.pdf,.docx"
        onChange={(e) => void handleFile(e.target.files?.[0])}
      />
      {error && (
        <p className="mt-2 text-xs text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
