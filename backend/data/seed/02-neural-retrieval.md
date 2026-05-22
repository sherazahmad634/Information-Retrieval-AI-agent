# Neural Information Retrieval

Neural IR replaces or augments lexical matching with learned representations. Two broad
families dominate practice: bi-encoders for first-stage retrieval, and cross-encoders for
second-stage re-ranking.

## Bi-Encoders (Dense Retrieval)

A bi-encoder maps a query and a document to fixed-size vectors independently. Similarity
between the two vectors — usually dot product or cosine — approximates semantic relevance.
Because both encodings are independent, documents can be embedded once at index time and
searched at scale using approximate-nearest-neighbour algorithms (HNSW, IVF-PQ, ScaNN).

DPR (Karpukhin et al., 2020) was an early breakthrough; modern systems use models such as
``all-MiniLM-L6-v2``, ``bge-base-en-v1.5``, ``E5``, and OpenAI's ``text-embedding-3-small``.

## Cross-Encoders (Re-ranking)

A cross-encoder concatenates the query and the document into a single input, runs them
through a transformer, and predicts a scalar relevance score. Because it sees both sides
jointly, it is significantly more accurate than a bi-encoder, but it cannot be pre-computed:
every query/document pair must be scored at query time. The standard recipe is therefore to
retrieve a few hundred candidates with a bi-encoder, then re-rank the top 20 to 100 with a
cross-encoder.

## Hybrid Retrieval

Lexical (BM25) and dense methods exhibit complementary error modes: BM25 excels at exact
keyword and rare-term matching while dense retrieval handles paraphrase. Combining them via
Reciprocal Rank Fusion (RRF) or learned blending consistently outperforms either branch
alone on benchmarks like BEIR and MTEB.

## Pitfalls

- **Domain shift** — models trained on web text degrade on legal or biomedical corpora.
- **Embedding drift** — re-embed the corpus whenever the model version changes.
- **Chunk boundary effects** — overly long chunks dilute the signal; overly short chunks
  lose context. Sentence-aware sliding windows around 256–512 tokens are a robust default.
