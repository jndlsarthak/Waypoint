import { Info } from "lucide-react";

export function DisclaimerBar() {
  return (
    <div className="border-b border-border bg-surface-muted">
      <p className="mx-auto flex max-w-5xl items-center gap-2 px-6 py-2 text-xs text-ink-muted">
        <Info size={13} strokeWidth={2} className="shrink-0 text-ink-muted" />
        General information from public IRCC guidance — not immigration or legal
        advice, and no substitute for a licensed RCIC or immigration lawyer.
      </p>
    </div>
  );
}
