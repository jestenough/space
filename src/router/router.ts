import { DEFAULT_LANG, isLangCode, normalizeLang } from "@/core/languages";
import type { Lang, Route } from "@/core/types";
import { safeDecodeURIComponent } from "@/core/url";

export const SYSTEM_SECTION = "site";
export const SECTIONS = [SYSTEM_SECTION, "about", "projects", "notes", "articles", "tags"] as const;

export const toLang = (value: string | undefined): Lang => normalizeLang(value);

const decodedSegment = (value: string | undefined): string | null => value === undefined ? null : safeDecodeURIComponent(value);
const isSection = (value: string | undefined): value is string => Boolean(value && SECTIONS.includes(value as (typeof SECTIONS)[number]));

export const parseRoute = (): Route => {
  const path = window.location.pathname.replace(/^\/+|\/+$/g, "");
  if (!path) return { lang: DEFAULT_LANG, page: "section", section: SYSTEM_SECTION };

  const [langCandidate, section, slug, extra] = path.split("/");
  if (!isLangCode(langCandidate)) return { lang: DEFAULT_LANG, page: "not-found", slug: path };

  const lang = normalizeLang(langCandidate);
  if (extra) return { lang, page: "not-found", slug: path };
  if (section === undefined) return { lang, page: "section", section: SYSTEM_SECTION };

  if (section === "articles" && slug) {
    const decodedSlug = decodedSegment(slug);
    return decodedSlug ? { lang, page: "article", slug: decodedSlug } : { lang, page: "not-found", slug: path };
  }

  if (section === "tags" && slug) {
    const decodedTag = decodedSegment(slug);
    return decodedTag ? { lang, page: "tags", tag: decodedTag } : { lang, page: "not-found", slug: path };
  }

  if (isSection(section) && !slug) return section === "articles" ? { lang, page: "articles" } : section === "tags" ? { lang, page: "tags" } : { lang, page: "section", section };

  if (isSection(section) && slug) {
    const decodedSlug = decodedSegment(slug);
    return decodedSlug ? { lang, page: "info-file", section, slug: decodedSlug } : { lang, page: "not-found", slug: path };
  }

  if (section && !slug) {
    const decodedSlug = decodedSegment(section);
    return decodedSlug ? { lang, page: "info-file", section: SYSTEM_SECTION, slug: decodedSlug } : { lang, page: "not-found", slug: path };
  }

  return { lang, page: "not-found", slug: path };
};

export const navigateHome = (lang: Lang): void => {
  window.location.href = `/${lang}`;
};
