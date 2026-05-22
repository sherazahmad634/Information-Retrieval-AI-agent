# IR-Agent — REST API Reference

Base URL (default): `http://localhost:8000/api/v1`

Interactive Swagger UI is mounted at `/docs`; ReDoc at `/redoc`; raw OpenAPI
JSON at `/openapi.json`.

## Authentication

If `API_KEY` is set in the environment, every endpoint requires:

```
X-API-Key: <your-key>
```

Set `X-Session-ID: <uuid>` on chat requests to keep working memory keyed to
the same conversation across turns; the frontend generates and reuses one
automatically.

## Error Format

All errors return a uniform JSON body:

```json
{
  "code": "not_found",
  "message": "Document not found.",
  "details": {},
  "request_id": "8a7f9c1d2e..."
}
```

| HTTP | `code`              | Meaning                                  |
|------|---------------------|------------------------------------------|
| 401  | `unauthorized`      | Missing/invalid API key                  |
| 404  | `not_found`         | Resource doesn't exist                   |
| 413  | _native_            | Upload exceeds size cap                  |
| 422  | `validation_error`  | Pydantic request validation failed       |
| 429  | `rate_limited`      | Rate limiter exceeded                    |
| 500  | `internal_error`    | Unhandled server-side fault              |
| 502  | `llm_error`         | LLM provider failure                     |
| 503  | `retrieval_error`   | Retrieval pipeline failure               |

---

## Endpoints

### `GET /health`

Liveness probe plus corpus statistics.

**Response 200**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "document_count": 5,
  "chunk_count": 47
}
```

### `GET /tools`

List the agent's registered tools.

**Response 200**

```json
{
  "items": [
    {
      "name": "document_search",
      "description": "Search the user's private indexed document corpus…",
      "parameters": { "type": "object", "properties": { … } }
    }
  ],
  "total": 6
}
```

### `GET /documents`

List indexed documents (newest first).

**Response 200** — `DocumentList`

### `POST /documents/upload`

Multipart upload of a single document.

**Form fields**

| Field   | Type | Required | Description                          |
|---------|------|----------|--------------------------------------|
| `file`  | file | yes      | `.txt`, `.md`, `.html`, `.pdf`, `.docx` |
| `title` | text | no       | Override the auto-derived title      |

**Response 201** — `IngestResponse`

```json
{
  "document_id": "5f3c…",
  "title": "report.pdf",
  "chunks_created": 14,
  "char_count": 8327
}
```

### `POST /documents/ingest-seed`

Ingest every file under `SEED_CORPUS_PATH` (defaults to the bundled corpus).
Idempotent only in the sense that re-running it adds *new* copies — delete
first if you want a clean re-ingest.

**Response 200** — `BulkIngestResponse`

### `DELETE /documents/{document_id}`

Remove a document and all its chunks. Returns `204 No Content` on success.

### `POST /search`

Direct hybrid retrieval — useful for debugging and for clients that don't need
LLM grounding.

**Request body**

```json
{
  "query": "What is reciprocal rank fusion?",
  "top_k": 5,
  "use_reranker": true,
  "filters": null
}
```

**Response 200** — `SearchResponse` with ranked `CitationChunk` items.

### `POST /chat`

Single-turn agentic Q&A. Runs the function-calling loop and returns the final
answer plus citations.

**Request body**

```json
{
  "query": "Summarise the neural retrieval doc.",
  "history": [
    { "role": "user", "content": "earlier turn" },
    { "role": "assistant", "content": "earlier response" }
  ],
  "top_k": 5,
  "temperature": 0.2
}
```

**Headers**

| Header           | Purpose                                                |
|------------------|--------------------------------------------------------|
| `X-Session-ID`   | Working-memory session key (UUID recommended)          |
| `X-API-Key`      | Required when the server is launched with `API_KEY`    |

**Response 200** — `ChatResponse`

```json
{
  "answer": "Reciprocal rank fusion combines… [1] [2]",
  "citations": [
    { "chunk_id": "…", "document_title": "Neural Retrieval", "text": "…", "score": 0.87, "source": "rerank", "position": 3 }
  ],
  "elapsed_ms": 842.3
}
```

### `POST /chat/stream`

Same payload as `/chat`, but the response is a Server-Sent-Events stream.

**Event types**

| Event       | Data                                                                |
|-------------|---------------------------------------------------------------------|
| `trace`     | `{ tool, arguments, summary }` — one per tool invocation            |
| `citations` | `Citation[]`                                                        |
| `token`     | `string` — incremental text token                                   |
| `done`      | `{ elapsed_ms, iterations }`                                        |

**Example consumer (curl)**

```bash
curl -N -H "Content-Type: application/json" \
     -H "X-Session-ID: 11111111-2222-3333-4444-555555555555" \
     -d '{"query":"What is BM25?"}' \
     http://localhost:8000/api/v1/chat/stream
```

---

## Schemas (excerpt)

```ts
interface Citation {
  chunk_id: string;
  document_id: string;
  document_title: string;
  text: string;
  score: number;
  source: "dense" | "bm25" | "hybrid" | "rerank";
  position: number;
}

interface ChatResponse {
  answer: string;
  citations: Citation[];
  elapsed_ms: number;
}
```

Full schemas are emitted in `openapi.json` and rendered live at `/docs`.
