import Link from "next/link";
import { Code2 } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur-sm">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="font-display text-xl font-medium tracking-tight text-ink">
            Waypoint
          </span>
          <span className="hidden text-sm text-ink-muted sm:inline">
            Canadian study &amp; work guidance
          </span>
        </Link>
        <Link
          href="https://github.com/jndlsarthak/Waypoint"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 rounded-full border border-border px-3.5 py-1.5 text-sm text-ink-muted transition hover:border-accent/40 hover:text-ink"
        >
          <Code2 size={15} strokeWidth={1.75} />
          Source
        </Link>
      </div>
    </header>
  );
}
