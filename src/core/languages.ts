import type { Lang } from "@/core/types";

export const DEFAULT_LANG: Lang = "en";

const LANG_PATTERN = /^[a-z]{2,3}(?:-[A-Za-z]{2})?$/;

export const isLangCode = (value: string | undefined | null): value is Lang => {
  return typeof value === "string" && LANG_PATTERN.test(value);
};

export const normalizeLang = (value: string | undefined | null, defaultLang: Lang = DEFAULT_LANG): Lang => {
  if (!isLangCode(value)) return defaultLang;
  const [base, region] = value.split("-");
  return region ? `${base.toLowerCase()}-${region.toUpperCase()}` : base.toLowerCase();
};
