"use client";

/**
 * Conversation state hook for the chat interface.
 *
 * Maintains the message list, sends user turns, and consumes the agent's
 * streaming response (citations + traces + tokens).
 */

import { useCallback, useState } from "react";

import { chatStream } from "@/lib/api";
import type { AgentTraceEvent, Citation, ChatMessage } from "@/lib/types";

export interface UIMessage extends ChatMessage {
  id: string;
  citations?: Citation[];
  traces?: AgentTraceEvent[];
  elapsed_ms?: number;
  iterations?: number;
  pending?: boolean;
}

export function useChat() {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isStreaming) return;

      setError(null);
      const userMsg: UIMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        content: trimmed,
      };
      const assistantId = `a-${Date.now()}`;
      const placeholder: UIMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        citations: [],
        traces: [],
        pending: true,
      };
      setMessages((prev) => [...prev, userMsg, placeholder]);
      setIsStreaming(true);

      const history: ChatMessage[] = messages
        .filter((m) => !m.pending && m.content)
        .map(({ role, content }) => ({ role, content }));

      try {
        for await (const event of chatStream(trimmed, history)) {
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              switch (event.event) {
                case "trace":
                  return { ...m, traces: [...(m.traces ?? []), event.data] };
                case "citations":
                  return { ...m, citations: event.data };
                case "token":
                  return { ...m, content: m.content + event.data };
                case "done":
                  return {
                    ...m,
                    pending: false,
                    elapsed_ms: event.data.elapsed_ms,
                    iterations: event.data.iterations,
                  };
              }
            }),
          );
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        setError(msg);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: `Error: ${msg}`, pending: false }
              : m,
          ),
        );
      } finally {
        setIsStreaming(false);
      }
    },
    [isStreaming, messages],
  );

  return { messages, isStreaming, error, send, reset };
}
