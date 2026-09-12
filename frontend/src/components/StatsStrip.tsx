const STATS = [
  { value: "22/22", label: "Scope-handling accuracy" },
  { value: "13/13", label: "Citations with zero hallucinated sources" },
  { value: "10", label: "Official IRCC source pages" },
  { value: "224", label: "Indexed guidance chunks" },
];

export function StatsStrip() {
  return (
    <section className="mx-auto max-w-3xl px-6 pb-16">
      <div className="grid grid-cols-2 divide-y divide-border rounded-2xl border border-border bg-surface sm:grid-cols-4 sm:divide-x sm:divide-y-0">
        {STATS.map((stat) => (
          <div
            key={stat.label}
            className="flex flex-col items-center gap-1 px-4 py-6 text-center"
          >
            <span className="font-display text-2xl font-medium text-ink">
              {stat.value}
            </span>
            <span className="text-xs leading-snug text-ink-muted">
              {stat.label}
            </span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-center text-xs text-ink-muted">
        From the golden-set eval —{" "}
        <a
          href="https://github.com/jndlsarthak/Waypoint/blob/main/eval/results.json"
          target="_blank"
          rel="noopener noreferrer"
          className="underline decoration-border underline-offset-2 hover:text-ink"
        >
          see results.json
        </a>
        .
      </p>
    </section>
  );
}
