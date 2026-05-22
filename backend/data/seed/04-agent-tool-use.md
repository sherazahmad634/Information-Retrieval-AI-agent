# Tool-Using Agents

An AI agent is a system that decides which actions to take in pursuit of a goal. When
those actions are calls to deterministic external functions — search, calculation,
database queries, web requests — we call it a **tool-using** or **function-calling**
agent. Tool use turns a language model into an interactive system that can observe and
act, not just produce text.

## ReAct

The ReAct paradigm (Yao et al., 2022) interleaves *reasoning* traces with *actions*. At
each step the model emits either a "Thought" that decomposes the problem or an "Action"
that invokes a tool. The tool's output is fed back as an "Observation", and the loop
continues until the model emits a final answer.

## Function Calling APIs

OpenAI, Anthropic, and most open-source models now support structured function calling:
the developer supplies a JSON schema for each tool, and the model responds with a typed
arguments object instead of free-form text. This eliminates output-parsing brittleness
and lets multiple tool calls execute in parallel.

## Designing Good Tools

- **Narrow** — each tool should do one thing. A bloated tool is hard for the model to
  invoke correctly.
- **Descriptive names and docs** — the model relies entirely on these to choose. Spell
  out *when* to call the tool, not just *what* it does.
- **Forgiving inputs, strict outputs** — accept loosely-shaped inputs but always return a
  predictable structure.
- **Cheap and fast** — agents call tools many times. Keep latency under a second where
  possible.

## Common Failure Modes

- **Overuse** — calling search for trivia the model already knows.
- **Underuse** — answering from parametric knowledge when retrieval would be safer.
- **Bad arguments** — passing the wrong field names; mitigated by strict JSON-schema
  validation.
- **Infinite loops** — invoking the same tool over and over without progress; mitigated
  with a max-iterations cap and trace inspection.
