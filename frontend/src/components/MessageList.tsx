"use client";

import { useEffect, useRef } from "react";

import { MessageBubble } from "@/components/MessageBubble";
import type { UIMessage } from "@/hooks/useChat";

interface MessageListProps {
  messages: UIMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center px-6 py-20 text-center">
        <h2 className="text-2xl font-semibold tracking-tight">
          Ask anything about your documents
        </h2>
        <p className="mt-3 max-w-md text-sm text-ink-500">
          IR-Agent searches your indexed corpus, falls back to the open web when
          needed, remembers facts you tell it, and cites every claim it makes.
        </p>
        <div className="mt-8 grid w-full grid-cols-1 gap-2 text-left sm:grid-cols-2">
          {[
            "What is reciprocal rank fusion?",
            "Summarise the seed corpus on neural retrieval.",
            "Calculate sqrt(2) * pi",
            "Remember that I prefer concise answers",
          ].map((s) => (
            <div
              key={s}
              className="rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-700 shadow-card dark:border-ink-700 dark:bg-ink-900 dark:text-ink-100"
            >
              {s}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-6">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
