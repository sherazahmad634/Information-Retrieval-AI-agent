# Information Retrieval Fundamentals

Information Retrieval (IR) is the science of finding material — usually unstructured text —
that satisfies an information need from within a large collection. Classic IR contrasts with
data retrieval (exact match against structured records) in two ways: queries are typically
ambiguous, and relevance is graded rather than binary.

## The Vector Space Model

The vector space model represents documents and queries as vectors in a high-dimensional
term space. Cosine similarity between the query vector and a document vector approximates
relevance. Term weights are most commonly computed using TF-IDF, which combines term
frequency with inverse document frequency to down-weight common words.

## BM25

Okapi BM25 is a probabilistic ranking function that, despite being introduced in the 1990s,
remains the dominant lexical baseline. It uses a saturated TF component (so additional
occurrences of a term yield diminishing returns), a length normalization factor, and an
IDF weighting derived from a binary independence model.

## Evaluation

Standard offline metrics include:

- **Precision@k** — fraction of the top-k results that are relevant.
- **Recall@k** — fraction of all relevant documents retrieved in the top-k.
- **Mean Average Precision (MAP)** — average of per-query precision across recall levels.
- **Normalized Discounted Cumulative Gain (NDCG)** — accounts for graded relevance and
  ranking order, normalising against the ideal ranking.
- **Mean Reciprocal Rank (MRR)** — particularly useful for navigational queries where there
  is essentially one correct answer.

Modern systems also rely on click-through rate, session abandonment, and explicit user
feedback for online evaluation.
