"""Tool-using RAG agent.

This is the heart of the system. The agent runs an OpenAI-style
function-calling loop:

    1. Send the user query + conversation history + tool catalogue to the LLM.
    2. If the LLM responds with one or more ``tool_calls``, dispatch each via
       the :class:`ToolRegistry` in parallel.
    3. Append the tool results to the conversation and loop.
    4. Stop when the LLM returns a final assistant message (no tool calls) or
       the ``max_iterations`` safety cap is reached.

The agent works with any OpenAI-compatible chat endpoint, including the
official OpenAI API, Azure OpenAI, Ollama, and llama-cpp-python's server.
A fully-deterministic mock mode is also supported for offline testing.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.models.schemas import ChatMessage, CitationChunk
from app.repositories.document_store import DocumentStore
from app.services.memory import MemoryService, WorkingMemory
from app.services.tools.base import ToolError
from app.services.tools.registry import ToolRegistry

logger = get_logger(__name__)


_SYSTEM_PROMPT = """You are IR-Agent, a research assistant specialised in Information Retrieval.

Core behaviour
--------------
* Whenever the user asks a question, FIRST call `document_search` to look for
  the answer in their indexed corpus. Prefer corpus evidence over your own
  knowledge.
* If `document_search` returns nothing useful and the question is about fresh
  or external information, call `web_search`. Otherwise say you don't know.
* When the user asks you to remember a fact, call `remember`. When the user
  refers to themselves or their preferences, consider calling `recall` first.
* When the user asks for a calculation, call `calculator` — never guess
  arithmetic.
* When the user provides new information they want preserved, call
  `document_ingest`.

Answer style
------------
* Cite every factual claim using bracketed indices that map to the
  `document_search` results, e.g. "[1]", "[2]".
* Be concise and accurate. If sources disagree, say so.
* Never fabricate citations. If you used `web_search`, mention the URL.
"""


@dataclass(slots=True)
class AgentTrace:
    """Diagnostic record of one tool invocation, surfaced to the UI."""

    tool: str
    arguments: dict[str, Any]
    summary: str


@dataclass(slots=True)
class AgentResponse:
    """Final output of a single agent turn."""

    answer: str
    citations: list[CitationChunk]
    traces: list[AgentTrace]
    iterations: int
    elapsed_ms: float


class ToolUsingAgent:
    """Function-calling agent that orchestrates tools, retrieval, and memory."""

    def __init__(
        self,
        *,
        openai_client: Any,
        model: str,
        tools: ToolRegistry,
        document_store: DocumentStore,
        working_memory: WorkingMemory,
        long_term_memory: MemoryService,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        max_iterations: int = 6,
        use_mock: bool = False,
    ) -> None:
        self._client = openai_client
        self._model = model
        self._tools = tools
        self._document_store = document_store
        self._working_memory = working_memory
        self._long_term_memory = long_term_memory
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._max_iterations = max_iterations
        self._use_mock = use_mock

    # ------------------------------------------------------------------ Public

    async def chat(
        self,
        *,
        query: str,
        session_id: str | None = None,
        history: Sequence[ChatMessage] | None = None,
        temperature: float | None = None,
    ) -> AgentResponse:
        """Run one agentic turn and return the assembled answer."""
        sid = session_id or str(uuid.uuid4())
        started = time.perf_counter()

        messages = await self._build_initial_messages(sid, query, history)
        traces: list[AgentTrace] = []
        citation_chunks: list[dict[str, Any]] = []

        iterations = 0
        for iteration in range(self._max_iterations):
            iterations = iteration + 1
            completion = await self._llm_chat(messages, temperature=temperature)
            choice = completion["choices"][0]["message"]
            messages.append(_clean_assistant_message(choice))

            tool_calls = choice.get("tool_calls") or []
            if not tool_calls:
                break

            tool_messages, new_traces, new_citations = await self._run_tool_calls(tool_calls)
            traces.extend(new_traces)
            citation_chunks.extend(new_citations)
            messages.extend(tool_messages)
        else:
            logger.warning("agent_iteration_cap_hit", cap=self._max_iterations)

        answer = (choice.get("content") or "").strip() or "I was unable to produce an answer."
        await self._working_memory.append(sid, ChatMessage(role="user", content=query))
        await self._working_memory.append(sid, ChatMessage(role="assistant", content=answer))

        citations = await self._build_citations(citation_chunks)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "agent_turn_complete",
            session_id=sid,
            iterations=iterations,
            tools=len(traces),
            citations=len(citations),
            ms=elapsed_ms,
        )
        return AgentResponse(
            answer=answer,
            citations=citations,
            traces=traces,
            iterations=iterations,
            elapsed_ms=elapsed_ms,
        )

    async def stream(
        self,
        *,
        query: str,
        session_id: str | None = None,
        history: Sequence[ChatMessage] | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield Server-Sent-Event-friendly dicts as the agent works.

        Events:
        * ``trace``     — ``{"tool": ..., "arguments": ..., "summary": ...}``
        * ``citations`` — list of :class:`CitationChunk` dicts
        * ``token``     — incremental text token from the final answer
        * ``done``      — ``{"elapsed_ms": ..., "iterations": ...}``
        """
        response = await self.chat(
            query=query, session_id=session_id, history=history, temperature=temperature
        )
        for trace in response.traces:
            yield {
                "event": "trace",
                "data": {
                    "tool": trace.tool,
                    "arguments": trace.arguments,
                    "summary": trace.summary,
                },
            }
        yield {"event": "citations", "data": [c.model_dump() for c in response.citations]}
        # Stream the final answer in word-sized chunks for a smooth typewriter UI.
        for token in response.answer.split(" "):
            yield {"event": "token", "data": token + " "}
            await asyncio.sleep(0)
        yield {
            "event": "done",
            "data": {"elapsed_ms": response.elapsed_ms, "iterations": response.iterations},
        }

    # ------------------------------------------------------------------ Private

    async def _build_initial_messages(
        self,
        session_id: str,
        query: str,
        history: Sequence[ChatMessage] | None,
    ) -> list[dict[str, Any]]:
        long_term = await self._long_term_memory.all()
        memory_block = (
            "\n\nLong-term memory:\n"
            + "\n".join(f"- {k}: {v}" for k, v in long_term.items())
            if long_term
            else ""
        )
        system_content = f"{_SYSTEM_PROMPT}{memory_block}"

        working_history = await self._working_memory.history(session_id)
        combined_history = list(history or []) + working_history

        msgs: list[dict[str, Any]] = [{"role": "system", "content": system_content}]
        for h in combined_history:
            msgs.append({"role": h.role, "content": h.content})
        msgs.append({"role": "user", "content": query})
        return msgs

    async def _llm_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float | None,
    ) -> dict[str, Any]:
        if self._use_mock:
            return _mock_completion(messages, self._tools)
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=self._tools.openai_schemas(),
                tool_choice="auto",
                temperature=temperature if temperature is not None else self._temperature,
                max_tokens=self._max_tokens,
            )
            return completion.model_dump()
        except Exception as exc:
            logger.exception("llm_chat_failed")
            raise LLMError("LLM chat completion failed.", details={"reason": str(exc)}) from exc

    async def _run_tool_calls(
        self, tool_calls: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[AgentTrace], list[dict[str, Any]]]:
        async def run_one(call: dict[str, Any]) -> tuple[dict[str, Any], AgentTrace, list[dict[str, Any]]]:
            fn = call["function"]
            name = fn["name"]
            try:
                arguments = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError as exc:
                arguments = {}
                content = f"Invalid JSON arguments: {exc}"
                trace = AgentTrace(tool=name, arguments={}, summary=content)
                return (
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": name,
                        "content": content,
                    },
                    trace,
                    [],
                )
            try:
                result = await self._tools.invoke(name, arguments)
                summary = result.content[:240]
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "name": name,
                    "content": result.content,
                }
                citations: list[dict[str, Any]] = []
                if name == "document_search":
                    citations = result.data.get("results", []) or []
                return tool_msg, AgentTrace(name, arguments, summary), citations
            except ToolError as exc:
                content = f"Tool error: {exc}"
                return (
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": name,
                        "content": content,
                    },
                    AgentTrace(name, arguments, content),
                    [],
                )

        results = await asyncio.gather(*(run_one(c) for c in tool_calls))
        tool_msgs = [r[0] for r in results]
        traces = [r[1] for r in results]
        citations: list[dict[str, Any]] = []
        for r in results:
            citations.extend(r[2])
        return tool_msgs, traces, citations

    async def _build_citations(
        self, raw_chunks: list[dict[str, Any]]
    ) -> list[CitationChunk]:
        # De-duplicate by chunk_id (the agent may have searched multiple times).
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for ch in raw_chunks:
            cid = ch.get("chunk_id")
            if not cid or cid in seen:
                continue
            seen.add(cid)
            unique.append(ch)

        titles: dict[str, str] = {}
        for ch in unique:
            doc_id = ch.get("document_id", "")
            if doc_id and doc_id not in titles:
                doc = await self._document_store.get(doc_id)
                titles[doc_id] = doc.title if doc else "Unknown"

        return [
            CitationChunk(
                chunk_id=ch["chunk_id"],
                document_id=ch.get("document_id", ""),
                document_title=titles.get(ch.get("document_id", ""), "Unknown"),
                text=ch.get("text", ""),
                score=float(ch.get("score", 0.0)),
                source=ch.get("source", "hybrid"),
                position=int(ch.get("position", 0)),
            )
            for ch in unique
        ]


def _clean_assistant_message(message: dict[str, Any]) -> dict[str, Any]:
    """Strip provider-specific null fields before echoing back to the LLM.

    OpenAI returns assistant messages with extra null fields (``function_call``,
    ``refusal``, ``audio``) that some compatible providers (e.g. Groq) reject
    when echoed into a follow-up request. Keep only the canonical fields and
    drop any whose value is ``None``.
    """
    keep = {"role", "content", "tool_calls", "name"}
    cleaned: dict[str, Any] = {}
    for key in keep:
        if key in message and message[key] is not None:
            cleaned[key] = message[key]
    # `content` must be present (can be empty string) when there are tool_calls.
    if "tool_calls" in cleaned and "content" not in cleaned:
        cleaned["content"] = ""
    if "role" not in cleaned:
        cleaned["role"] = "assistant"
    return cleaned


# ---------------------------------------------------------------------------
# Mock completion (used when OPENAI is unavailable / MOCK_LLM=true)
# ---------------------------------------------------------------------------


def _mock_completion(messages: list[dict[str, Any]], tools: ToolRegistry) -> dict[str, Any]:
    """Deterministic mock that calls ``document_search`` once, then answers.

    Useful for unit tests and demos without an OPENAI key. The mock's
    behaviour:

    * If the last assistant message has no ``tool_calls`` yet and the
      ``document_search`` tool is registered, it emits a single tool call.
    * Otherwise, it returns a stitched answer derived from prior tool results.
    """
    user_q = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    last = messages[-1] if messages else {}

    # If we have not yet called document_search, do so.
    has_doc_search = tools.get("document_search") is not None
    already_searched = any(
        m.get("role") == "tool" and m.get("name") == "document_search" for m in messages
    )
    if has_doc_search and not already_searched and last.get("role") != "tool":
        return {
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": f"call_{uuid.uuid4().hex[:8]}",
                                "type": "function",
                                "function": {
                                    "name": "document_search",
                                    "arguments": json.dumps({"query": user_q, "top_k": 5}),
                                },
                            }
                        ],
                    },
                }
            ]
        }

    # Stitch a deterministic answer from any tool outputs we already have.
    tool_text = " ".join(
        m.get("content", "")[:400] for m in messages if m.get("role") == "tool"
    ).strip()
    answer = (
        f"Based on the indexed corpus: {tool_text[:600]}"
        if tool_text
        else f"I do not have indexed information about: {user_q}."
    )
    return {
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": answer, "tool_calls": []},
            }
        ]
    }
