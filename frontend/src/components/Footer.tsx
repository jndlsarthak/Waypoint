import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-auto border-t border-border bg-surface-muted">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-10 sm:flex-row sm:items-start sm:justify-between">
        <p className="max-w-md text-xs leading-relaxed text-ink-muted">
          This tool provides general information based on public IRCC
          guidance. It is not immigration or legal advice and does not
          replace a licensed RCIC (Regulated Canadian Immigration Consultant)
          or immigration lawyer. It does not make eligibility determinations
          for individuals and does not collect or store any personal or
          case-specific information.
        </p>
        <div className="flex flex-col gap-2 text-sm">
          <Link
            href="https://github.com/jndlsarthak/Waypoint"
            target="_blank"
            rel="noopener noreferrer"
            className="text-ink-muted underline decoration-border underline-offset-2 hover:text-ink"
          >
            View source on GitHub
          </Link>
          <span className="text-xs text-ink-muted">
            Non-commercial portfolio project.
          </span>
        </div>
      </div>
    </footer>
  );
}
