import Link from "next/link";

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur-sm">
      <div className="mx-auto flex max-w-5xl items-center px-6 py-4">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="font-display text-xl font-medium tracking-tight text-ink">
            Waypoint
          </span>
          <span className="hidden text-sm text-ink-muted sm:inline">
            Canadian study &amp; work guidance
          </span>
        </Link>
      </div>
    </header>
  );
}
