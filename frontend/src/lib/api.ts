/**
 * Typed API client for the IR-Agent backend.
 *
 * The base URL is read from `NEXT_PUBLIC_API_URL`; if it is unset we fall
 * back to a same-origin `/api/proxy` path that the Next.js rewrite forwards.
 */

import type {
  ChatMessage,
  ChatResponse,
  ChatStreamEvent,
  DocumentList,
  HealthResponse,
  IngestResponse,
  SearchResponse,
  ToolListResponse,
} from "@/lib/types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ?? "/api/proxy";

const SESSION_HEADER = "X-Session-ID";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  const KEY = "ir-agent-session";
  let id = window.localStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(KEY, id);
  }
  return id;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      [SESSION_HEADER]: getSessionId(),
      ...(init?.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail: string = res.statusText;
    try {
      const body = await res.json();
      detail = body.message || body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ----------------------------------------------------------------------------
// Health / tools
// ----------------------------------------------------------------------------

export const getHealth = () => request<HealthResponse>("/health");
export const listTools = () => request<ToolListResponse>("/tools");

// ----------------------------------------------------------------------------
// Documents
// ----------------------------------------------------------------------------

export const listDocuments = () => request<DocumentList>("/documents");

export const uploadDocument = async (file: File, title?: string) => {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  return request<IngestResponse>("/documents/upload", {
    method: "POST",
    body: form,
  });
};

export const ingestSeed = () =>
  request<{ documents: IngestResponse[]; total_chunks: number }>(
    "/documents/ingest-seed",
    { method: "POST" },
  );

export const deleteDocument = (documentId: string) =>
  request<void>(`/documents/${documentId}`, { method: "DELETE" });

// ----------------------------------------------------------------------------
// Search & chat
// ----------------------------------------------------------------------------

export const search = (query: string, topK = 5) =>
  request<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK, use_reranker: true }),
  });

export const chat = (query: string, history: ChatMessage[] = []) =>
  request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ query, history, top_k: 5 }),
  });

/**
 * Open an SSE stream for the agentic chat endpoint.
 *
 * Returns an async iterator that yields parsed `ChatStreamEvent` payloads.
 */
export async function* chatStream(
  query: string,
  history: ChatMessage[] = [],
): AsyncGenerator<ChatStreamEvent> {
  const res = await fetch(`${BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      [SESSION_HEADER]: getSessionId(),
    },
    body: JSON.stringify({ query, history, top_k: 5, stream: true }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`Stream failed: ${res.status} ${res.statusText}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // SSE allows blocks separated by \n\n OR \r\n\r\n. sse-starlette emits \r\n,
  // so normalise all line endings to \n before parsing.
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    let separator: number;
    while ((separator = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, separator);
      buffer = buffer.slice(separator + 2);

      let event = "message";
      const dataLines: string[] = [];
      for (const raw of block.split("\n")) {
        const line = raw.trimEnd();
        if (!line || line.startsWith(":")) continue; // skip blanks / comments
        if (line.startsWith("event:")) {
          event = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trimStart());
        }
      }
      if (dataLines.length === 0) continue;
      const dataStr = dataLines.join("\n");
      let data: unknown;
      try {
        data = JSON.parse(dataStr);
      } catch {
        data = dataStr;
      }
      yield { event, data } as ChatStreamEvent;
    }
  }
}
