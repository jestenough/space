import { escapeHtml } from "@/core/escape";
import type { Lang } from "@/core/types";
import { text } from "@/ui/i18n";

export const missingTranslationCopy = (lang: Lang): { title: string; description: string } => ({
  title: text(lang).missingTranslationTitle,
  description: text(lang).missingTranslationDescription,
});

export const missingTranslationHtml = (lang: Lang, languages: readonly Lang[]): string => {
  const copy = missingTranslationCopy(lang);
  return `<section class="file-document"><h1>${escapeHtml(copy.title)}</h1><p>${escapeHtml(copy.description)}</p><p class="meta">available: ${escapeHtml(languages.join(", "))}</p></section>`;
};
