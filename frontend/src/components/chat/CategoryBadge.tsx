import type { Category } from "@/lib/api";

const CONFIG: Record<Category, { label: string; className: string }> = {
  factual: {
    label: "General guidance",
    className: "bg-accent-soft text-accent-strong",
  },
  individualized_advice: {
    label: "Consult a professional",
    className: "bg-rust-soft text-rust",
  },
  out_of_scope: {
    label: "Out of scope",
    className: "bg-surface-muted text-ink-muted",
  },
};

export function CategoryBadge({ category }: { category: Category }) {
  const { label, className } = CONFIG[category];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium ${className}`}
    >
      {label}
    </span>
  );
}
