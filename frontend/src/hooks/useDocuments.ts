"use client";

/**
 * Document-list state hook with refresh, upload, seed, and delete actions.
 */

import { useCallback, useEffect, useState } from "react";

import {
  deleteDocument,
  ingestSeed,
  listDocuments,
  uploadDocument,
} from "@/lib/api";
import type { DocumentSummary } from "@/lib/types";

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listDocuments();
      setDocuments(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to list documents");
    } finally {
      setLoading(false);
    }
  }, []);

  const upload = useCallback(
    async (file: File) => {
      await uploadDocument(file);
      await refresh();
    },
    [refresh],
  );

  const seed = useCallback(async () => {
    await ingestSeed();
    await refresh();
  }, [refresh]);

  const remove = useCallback(
    async (id: string) => {
      await deleteDocument(id);
      await refresh();
    },
    [refresh],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { documents, loading, error, refresh, upload, seed, remove };
}
