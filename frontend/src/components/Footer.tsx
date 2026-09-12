export function Footer() {
  return (
    <footer className="mt-auto border-t border-border bg-surface-muted">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-6 py-10">
        <p className="max-w-md text-xs leading-relaxed text-ink-muted">
          This tool provides general information based on public IRCC
          guidance. It is not immigration or legal advice and does not
          replace a licensed RCIC (Regulated Canadian Immigration Consultant)
          or immigration lawyer. It does not make eligibility determinations
          for individuals and does not collect or store any personal or
          case-specific information.
        </p>
        <span className="text-[11px] text-ink-muted/70">
          Non-commercial, educational project.
        </span>
      </div>
    </footer>
  );
}
