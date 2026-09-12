/**
 * The backend's own system prompt asks the model to append a "Sources"
 * section to its answer, but the UI renders sources itself from the
 * structured `sources` field (as proper cards with dates and links) — so we
 * cut the model's own trailing sources section out of the rendered prose to
 * avoid showing the same information twice, once as plain text and once as
 * designed cards.
 */
export function stripSourcesSection(markdown: string): string {
  const match = markdown.match(/\n+(\*\*sources\*\*|#{1,3}\s*sources\b|sources:)/i);
  if (!match || match.index === undefined) return markdown.trim();
  return markdown.slice(0, match.index).trim();
}

/**
 * The generation model is instructed to use plain ASCII citation brackets
 * ([1]) but occasionally reverts to full-width unicode brackets (【1】) —
 * a known quirk of the underlying model, not something the prompt fully
 * controls. Normalize on display so citations always look consistent.
 */
export function normalizeCitationBrackets(markdown: string): string {
  return markdown.replace(/【\s*(\d+)\s*】/g, "[$1]");
}
