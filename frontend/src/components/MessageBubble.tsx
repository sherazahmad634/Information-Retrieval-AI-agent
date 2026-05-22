"use client";

import clsx from "clsx";
import { Bot, User } from "lucide-react";
import { useState } from "react";

import { SourceCard } from "@/components/SourceCard";
import { ToolBadge } from "@/components/ToolBadge";
import type { UIMessage } from "@/hooks/useChat";

interface MessageBubbleProps {
  message: UIMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [open, setOpen] = useState(false);
  const isUser = message.role === "user";
  const hasCitations = !isUser && (message.citations?.length ?? 0) > 0;
  const hasTraces = !isUser && (message.traces?.length ?? 0) > 0;

  return (
    <article
      className={clsx(
        "flex gap-3 rounded-xl px-4 py-3 shadow-card",
        isUser
          ? "ml-auto max-w-[80%] bg-accent-600 text-white"
          : "max-w-full bg-white text-ink-900",
      )}
    >
      <div
        className={clsx(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
          isUser
            ? "bg-white/20 text-white"
            : "bg-accent-500/10 text-accent-600",
        )}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </div>
      <div className="min-w-0 flex-1">
        {hasTraces && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {message.traces?.map((t, i) => (
              <ToolBadge key={`${t.tool}-${i}`} trace={t} />
            ))}
          </div>
        )}
        <p
          className={clsx(
            "prose-message whitespace-pre-wrap text-sm leading-relaxed",
            message.pending && !message.content && "text-ink-500",
          )}
        >
          {message.content || (message.pending ? "Thinking…" : "")}
        </p>
        {hasCitations && (
          <div className="mt-3">
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="text-xs font-medium text-accent-600 hover:underline"
            >
              {open ? "Hide" : "Show"} {message.citations?.length} source
              {(message.citations?.length ?? 0) === 1 ? "" : "s"}
            </button>
            {open && (
              <div className="mt-2 grid gap-2">
                {message.citations?.map((c, i) => (
                  <SourceCard key={c.chunk_id} index={i + 1} citation={c} />
                ))}
              </div>
            )}
          </div>
        )}
        {!isUser && message.elapsed_ms !== undefined && (
          <p className="mt-2 text-[11px] text-ink-500">
            {message.iterations ?? 1} iteration
            {(message.iterations ?? 1) === 1 ? "" : "s"} ·{" "}
            {Math.round(message.elapsed_ms)} ms
          </p>
        )}
      </div>
    </article>
  );
}
