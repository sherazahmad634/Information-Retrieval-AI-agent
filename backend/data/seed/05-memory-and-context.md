# Memory and Context Management in AI Agents

A useful agent has to remember. Two kinds of memory are typically distinguished:

## Working Memory

Working memory is the short-term, in-context buffer of recent conversation turns. It is
bounded by the LLM's context window. Practical strategies include:

- **Rolling buffer** — keep the last *N* turns verbatim and drop the rest.
- **Summarisation** — when the buffer fills up, replace the oldest portion with a
  compressed summary produced by a cheaper model.
- **Recency-weighted retrieval** — index every prior turn and retrieve only the ones
  relevant to the current query.

## Long-Term Memory

Long-term memory persists across sessions. It can be implemented as:

- A **key/value store** for stable user facts ("user prefers metric units").
- A **vector store** of past conversations, retrieved by semantic similarity.
- A **structured knowledge graph** for entities and relations the agent should track.

The agent typically exposes long-term memory through `remember` and `recall` tools so
that writes are explicit and auditable.

## Context Window Management

Even with retrieval, prompts grow quickly. Three rules of thumb:

1. **Token budget per role** — allocate a fixed share of the context window to system
   prompt, history, retrieved passages, and the user's current message. Trim the lowest-
   priority slot first.
2. **Lossy compression beats truncation** — summarising old turns preserves more signal
   than dropping them entirely.
3. **Citations over copies** — instead of pasting whole documents, store a short
   reference and refetch on demand.

## Anti-Patterns

- **Implicit memory** — silently saving every utterance leads to surprises and privacy
  problems. Memory writes should always be intentional.
- **Stale facts** — without a TTL or revision mechanism, old preferences linger forever.
- **Conflating history with knowledge** — chat history belongs in working memory; verified
  facts belong in long-term memory; everything else belongs in the document corpus.
