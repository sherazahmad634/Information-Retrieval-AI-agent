"use client";

import { Loader2, RotateCcw, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { MessageList } from "@/components/MessageList";
import { useChat } from "@/hooks/useChat";

export function ChatInterface() {
  const { messages, isStreaming, error, send, reset } = useChat();
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    const text = input;
    setInput("");
    await send(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <section className="relative flex h-screen flex-1 flex-col">
      <header className="flex items-center justify-between border-b border-ink-100 bg-white/70 px-6 py-3 backdrop-blur dark:border-ink-700 dark:bg-ink-900/70">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">IR-Agent</h1>
          <p className="text-xs text-ink-500">
            Tool-using retrieval agent · grounded answers with citations
          </p>
        </div>
        <button
          type="button"
          onClick={reset}
          disabled={messages.length === 0 || isStreaming}
          className="inline-flex items-center gap-1 rounded-md border border-ink-200 px-3 py-1.5 text-sm text-ink-700 transition hover:bg-ink-100 disabled:opacity-40 dark:border-ink-700 dark:text-ink-100 dark:hover:bg-ink-700/40"
        >
          <RotateCcw className="h-3.5 w-3.5" /> New chat
        </button>
      </header>

      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} />
        {error && (
          <div className="mx-6 my-3 rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-ink-100 bg-white/80 px-4 py-3 backdrop-blur dark:border-ink-700 dark:bg-ink-900/80"
      >
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your documents…"
            rows={1}
            className="min-h-[44px] flex-1 resize-none rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 placeholder:text-ink-500 shadow-sm focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-500/30"
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="inline-flex h-11 items-center gap-1 rounded-lg bg-accent-600 px-4 text-sm font-medium text-white shadow-card transition hover:bg-accent-500 disabled:opacity-40"
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span>{isStreaming ? "Thinking…" : "Send"}</span>
          </button>
        </div>
      </form>
    </section>
  );
}
