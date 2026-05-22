"use client";

import { Library, Sparkles, Wrench } from "lucide-react";
import { useEffect, useState } from "react";

import { DocumentList } from "@/components/DocumentList";
import { DocumentUpload } from "@/components/DocumentUpload";
import { useDocuments } from "@/hooks/useDocuments";
import { getHealth, listTools } from "@/lib/api";
import type { HealthResponse, ToolDescriptor } from "@/lib/types";

export function Sidebar() {
  const { documents, loading, upload, seed, remove } = useDocuments();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [tools, setTools] = useState<ToolDescriptor[]>([]);
  const [seeding, setSeeding] = useState(false);

  useEffect(() => {
    void getHealth().then(setHealth).catch(() => setHealth(null));
    void listTools().then((r) => setTools(r.items)).catch(() => setTools([]));
  }, []);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await seed();
      const h = await getHealth();
      setHealth(h);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <aside className="flex w-full shrink-0 flex-col gap-4 border-r border-ink-100 bg-white/60 p-4 lg:w-80 dark:border-ink-700 dark:bg-ink-900/60">
      <div>
        <div className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <Sparkles className="h-4 w-4 text-accent-500" />
          IR-Agent
        </div>
        <p className="mt-1 text-[11px] text-ink-500">
          {health
            ? `${health.environment} · v${health.version} · ${health.document_count} docs · ${health.chunk_count} chunks`
            : "Connecting…"}
        </p>
      </div>

      <section>
        <header className="mb-2 flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-500">
            <Library className="h-3 w-3" /> Corpus
          </h2>
          <button
            type="button"
            onClick={handleSeed}
            disabled={seeding}
            className="text-[11px] font-medium text-accent-600 hover:underline disabled:opacity-50"
          >
            {seeding ? "Seeding…" : "Load seed"}
          </button>
        </header>
        <DocumentUpload onUpload={upload} />
        <div className="mt-3 max-h-72 overflow-y-auto">
          <DocumentList documents={documents} loading={loading} onDelete={remove} />
        </div>
      </section>

      <section className="mt-auto">
        <h2 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-500">
          <Wrench className="h-3 w-3" /> Agent tools
        </h2>
        <ul className="space-y-1">
          {tools.map((t) => (
            <li
              key={t.name}
              className="rounded border border-ink-100 bg-white px-2 py-1 text-[11px] leading-tight dark:border-ink-700 dark:bg-ink-900"
            >
              <p className="font-mono font-medium text-ink-900 dark:text-ink-50">
                {t.name}
              </p>
              <p className="line-clamp-2 text-ink-500">{t.description}</p>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );
}
