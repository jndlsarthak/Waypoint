import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CategoryBadge } from "@/components/chat/CategoryBadge";
import { ConflictBanner } from "@/components/chat/ConflictBanner";
import { SourceCard } from "@/components/chat/SourceCard";
import type { AnswerResponse } from "@/lib/api";
import { normalizeCitationBrackets, stripSourcesSection } from "@/lib/text";

export type ChatMessage =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "assistant"; response: AnswerResponse }
  | { id: string; role: "error"; content: string };

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex animate-fade-up justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-[15px] leading-relaxed text-white">
          {message.content}
        </div>
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div className="animate-fade-up rounded-xl border border-rust/30 bg-rust-soft px-4 py-3 text-sm text-rust">
        {message.content}
      </div>
    );
  }

  const { response } = message;
  const answerBody = normalizeCitationBrackets(stripSourcesSection(response.answer));

  return (
    <div className="flex animate-fade-up flex-col gap-3">
      <CategoryBadge category={response.category} />

      <div className="answer-prose text-[15px] leading-relaxed text-ink">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{answerBody}</ReactMarkdown>
      </div>

      <ConflictBanner conflicts={response.temporal_conflicts} />

      {response.sources.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2">
          {response.sources.map((source) => (
            <SourceCard key={source.n} source={source} />
          ))}
        </div>
      )}
    </div>
  );
}
