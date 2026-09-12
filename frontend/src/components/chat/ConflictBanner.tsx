import { TriangleAlert } from "lucide-react";
import type { TemporalConflict } from "@/lib/api";

export function ConflictBanner({
  conflicts,
}: {
  conflicts: TemporalConflict[];
}) {
  if (conflicts.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-amber/30 bg-amber-soft p-3">
      <div className="flex items-center gap-2 text-amber">
        <TriangleAlert size={15} strokeWidth={1.75} />
        <span className="text-xs font-medium">
          Guidance may have changed since one of these was last updated
        </span>
      </div>
      <ul className="flex flex-col gap-1 text-xs text-ink-muted">
        {conflicts.map((c, i) => (
          <li key={i}>
            Sources [{c.source_n_a}] ({c.date_a}) and [{c.source_n_b}] (
            {c.date_b}) cover similar ground but were last verified on
            different dates — worth double-checking both.
          </li>
        ))}
      </ul>
    </div>
  );
}
