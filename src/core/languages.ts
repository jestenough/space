import type { ArticleMeta, Lang } from "@/core/types";

export const DEFAULT_LANG: Lang = "en";
export const DEFAULT_HREFLANG = "x-default" as const;

const LANG_PATTERN = /^[a-z]{2,3}(?:-[A-Za-z]{2})?$/;
const DEFAULT_REGIONS: Record<string, string> = {
  en: "US",
  ru: "RU"
};

export const isLangCode = (value: string | undefined | null): value is Lang => {
  return typeof value === "string" && LANG_PATTERN.test(value);
};

export const normalizeLang = (value: string | undefined | null, defaultLang: Lang = DEFAULT_LANG): Lang => {
  if (!isLangCode(value)) return defaultLang;
  const [base, region] = value.split("-");
  return region ? `${base.toLowerCase()}-${region.toUpperCase()}` : base.toLowerCase();
};

export const formatLangLabel = (lang: Lang): string => {
  const normalized = normalizeLang(lang);
  const [baseRaw, regionRaw] = normalized.split("-");
  const base = baseRaw.toLowerCase();
  const region = (regionRaw ?? DEFAULT_REGIONS[base] ?? base).toUpperCase();
  return `${base}_${region}.UTF-8`;
};

export const formatOgLocale = (lang: Lang): string => formatLangLabel(lang).replace(".UTF-8", "");

export const pickLangText = (texts: Record<string, string>, lang: Lang): string => texts[lang] ?? "";

export const languagesFromArticles = (articles: readonly ArticleMeta[]): Lang[] => {
  const langs = new Set<Lang>();
  for (const article of articles) for (const lang of article.languages) langs.add(lang);
  if (langs.size === 0) langs.add(DEFAULT_LANG);
  return [...langs].sort((a, b) => a.localeCompare(b));
};

export const xDefaultPath = (paths: Partial<Record<Lang, string>>, preferredLang: Lang = DEFAULT_LANG): string | undefined => {
  return paths[preferredLang] ?? paths[Object.keys(paths).sort()[0] as Lang];
};
