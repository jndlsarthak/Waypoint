import { ArrowUpRight } from "lucide-react";
import type { Source } from "@/lib/api";

export function SourceCard({ source }: { source: Source }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex flex-col gap-1.5 rounded-xl border border-border bg-surface-muted/50 p-3 transition hover:border-accent/40 hover:bg-surface-muted"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-baseline gap-1.5">
          <span className="text-[11px] font-medium text-ink-muted">
            [{source.n}]
          </span>
          <span className="text-sm font-medium text-ink">
            {source.page_title}
          </span>
        </div>
        <ArrowUpRight
          size={14}
          strokeWidth={1.75}
          className="mt-0.5 shrink-0 text-ink-muted transition group-hover:text-accent"
        />
      </div>
      <p className="text-xs leading-snug text-ink-muted">
        {source.section_heading}
      </p>
      {source.date_last_modified && (
        <span className="mt-0.5 inline-flex w-fit items-center rounded-full bg-surface px-2 py-0.5 text-[11px] text-ink-muted">
          Last verified {source.date_last_modified}
        </span>
      )}
    </a>
  );
}
