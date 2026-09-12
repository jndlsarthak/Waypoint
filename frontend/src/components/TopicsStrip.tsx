import { Briefcase, Clock, GraduationCap } from "lucide-react";

const TOPICS = [
  {
    icon: GraduationCap,
    title: "Study permits",
    description: "Eligibility, how to apply, and what's required to study in Canada.",
  },
  {
    icon: Briefcase,
    title: "Post-graduation work permits",
    description: "Who qualifies for a PGWP, program-length rules, and field-of-study requirements.",
  },
  {
    icon: Clock,
    title: "Working while you study",
    description: "On-campus and off-campus work hours, and what counts as eligible work.",
  },
];

export function TopicsStrip() {
  return (
    <section className="mx-auto max-w-3xl px-6 pb-16">
      <div className="grid gap-4 sm:grid-cols-3">
        {TOPICS.map(({ icon: Icon, title, description }) => (
          <div
            key={title}
            className="flex flex-col gap-3 rounded-2xl border border-border bg-surface p-5"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
              <Icon size={17} strokeWidth={1.75} />
            </div>
            <h3 className="font-display text-base font-medium text-ink">
              {title}
            </h3>
            <p className="text-sm leading-snug text-ink-muted">
              {description}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
