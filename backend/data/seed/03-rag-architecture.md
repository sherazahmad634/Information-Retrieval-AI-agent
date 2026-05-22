# Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation, introduced by Lewis et al. (NeurIPS 2020), grounds a
large language model in an external knowledge source at inference time. RAG addresses two
chronic LLM weaknesses: factual hallucination and knowledge staleness.

## Standard Pipeline

1. **Ingestion** — parse source documents, split them into chunks, embed each chunk, and
   write the embeddings to a vector store.
2. **Query encoding** — embed the user's query with the same model used at ingestion.
3. **Retrieval** — find the top-k most similar chunks via approximate nearest-neighbour
   search, optionally combined with BM25 (hybrid retrieval).
4. **Re-ranking** — score the candidates with a cross-encoder for precision.
5. **Generation** — prompt the LLM with the user's query plus the retrieved passages, and
   instruct it to ground its answer and cite each claim.

## Best Practices

- **Sentence-aware chunking** with 256–512 tokens per chunk and 10–20% overlap.
- **Contextual chunk headers** — prepend the document title and section heading to each
  chunk so isolated passages remain interpretable.
- **Explicit citations** — instruct the model to reference each source with bracketed
  numbers ([1], [2]); always render them in the UI so the user can verify.
- **Refuse out-of-scope queries** — if retrieval returns no relevant chunks, the model
  should say so rather than fabricate.

## Agentic RAG

Modern systems treat retrieval as one of several tools an agent can choose to invoke. The
agent loop typically dispatches search, calls a calculator for arithmetic, and queries
external APIs for live data. This generalises the static RAG pipeline into a flexible
research assistant.
