/**
 * Shared TypeScript types mirroring the backend's Pydantic schemas.
 *
 * Keep these in sync with `backend/app/models/schemas.py`.
 */

export type Role = "user" | "assistant" | "system";

export interface ChatMessage {
  role: Role;
  content: string;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  document_title: string;
  text: string;
  score: number;
  source: string;
  position: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  elapsed_ms: number;
  tokens_used?: number | null;
}

export interface SearchResponse {
  query: string;
  results: Citation[];
  elapsed_ms: number;
}

export interface DocumentSummary {
  id: string;
  title: string;
  source: string;
  content_type: string;
  char_count: number;
  chunk_count: number;
  created_at: string;
}

export interface DocumentList {
  items: DocumentSummary[];
  total: number;
}

export interface IngestResponse {
  document_id: string;
  title: string;
  chunks_created: number;
  char_count: number;
}

export interface HealthResponse {
  status: "ok";
  version: string;
  environment: string;
  document_count: number;
  chunk_count: number;
}

export interface ToolDescriptor {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface ToolListResponse {
  items: ToolDescriptor[];
  total: number;
}

export interface AgentTraceEvent {
  tool: string;
  arguments: Record<string, unknown>;
  summary: string;
}

export type ChatStreamEvent =
  | { event: "trace"; data: AgentTraceEvent }
  | { event: "citations"; data: Citation[] }
  | { event: "token"; data: string }
  | { event: "done"; data: { elapsed_ms: number; iterations: number } };
