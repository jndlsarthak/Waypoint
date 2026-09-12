"use client";

import { useRef, useState } from "react";
import { ArrowUp } from "lucide-react";
import { MessageBubble, type ChatMessage } from "@/components/chat/MessageBubble";
import { askQuestion } from "@/lib/api";

const SUGGESTED_QUESTIONS = [
  "How many hours can I work off campus while studying?",
  "What are the eligibility requirements for a study permit?",
  "How long must my program be to qualify for a PGWP?",
];

function makeId() {
  return Math.random().toString(36).slice(2);
}

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  function scrollToBottom() {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    });
  }

  async function send(question: string) {
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;

    setMessages((prev) => [
      ...prev,
      { id: makeId(), role: "user", content: trimmed },
    ]);
    setInput("");
    setIsLoading(true);
    scrollToBottom();

    try {
      const response = await askQuestion(trimmed);
      setMessages((prev) => [
        ...prev,
        { id: makeId(), role: "assistant", response },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: "error",
          content:
            "Couldn't reach the assistant backend. Make sure the FastAPI server is running and NEXT_PUBLIC_API_BASE_URL points at it.",
        },
      ]);
    } finally {
      setIsLoading(false);
      scrollToBottom();
    }
  }

  return (
    <section className="mx-auto max-w-3xl px-6 pb-24">
      <div className="flex flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-[0_1px_2px_rgba(26,22,15,0.04)]">
        <div
          ref={scrollRef}
          className="flex min-h-[420px] max-h-[560px] flex-col gap-5 overflow-y-auto p-6"
        >
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-4 py-10 text-center">
              <p className="text-sm text-ink-muted">
                Try one of these, or ask your own question.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="rounded-full border border-border px-3.5 py-1.5 text-sm text-ink-muted transition hover:border-accent/40 hover:text-ink"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))
          )}

          {isLoading && (
            <div className="flex items-center gap-1.5 self-start rounded-full bg-surface-muted px-3.5 py-2">
              <span
                className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-ink-muted"
                style={{ animationDelay: "0ms" }}
              />
              <span
                className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-ink-muted"
                style={{ animationDelay: "160ms" }}
              />
              <span
                className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-ink-muted"
                style={{ animationDelay: "320ms" }}
              />
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex items-center gap-2 border-t border-border p-3"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about study permits, PGWP, working while studying…"
            className="flex-1 rounded-full bg-surface-muted px-4 py-2.5 text-[15px] text-ink placeholder:text-ink-muted/70 focus:outline-none focus:ring-2 focus:ring-accent/25"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            aria-label="Send"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-white transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ArrowUp size={18} strokeWidth={2} />
          </button>
        </form>
      </div>
    </section>
  );
}
