import { SYSTEM_SECTION } from "@/core/config";
import { DEFAULT_LANG, isLangCode, normalizeLang } from "@/core/languages";
import type { Lang, Route, SectionMeta } from "@/core/types";
import { safeDecodeURIComponent } from "@/core/url";

export const toLang = (value: string | undefined): Lang => normalizeLang(value);

const decodedSegment = (value: string | undefined): string | null => value === undefined ? null : safeDecodeURIComponent(value);
const systemSection = (sections: readonly SectionMeta[]): string => sections.find((section) => section.system)?.slug ?? SYSTEM_SECTION;
const sectionSlugs = (sections: readonly SectionMeta[]): Set<string> => new Set(sections.map((section) => section.slug));

export const parseRoute = (sections: readonly SectionMeta[] = []): Route => {
  const path = window.location.pathname.replace(/^\/+|\/+$/g, "");
  const system = systemSection(sections);
  if (!path) return { lang: DEFAULT_LANG, page: "section", section: system };

  const [langCandidate, section, slug, extra] = path.split("/");
  if (!isLangCode(langCandidate)) return { lang: DEFAULT_LANG, page: "not-found", slug: path };

  const lang = normalizeLang(langCandidate);
  if (extra) return { lang, page: "not-found", slug: path };
  if (section === undefined) return { lang, page: "section", section: system };

  const knownSections = sectionSlugs(sections);
  const isKnownSection = knownSections.has(section);

  if (section === "articles" && slug) {
    const decodedSlug = decodedSegment(slug);
    return decodedSlug ? { lang, page: "article", slug: decodedSlug } : { lang, page: "not-found", slug: path };
  }

  if (section === "tags" && slug) {
    const decodedTag = decodedSegment(slug);
    return decodedTag ? { lang, page: "tags", tag: decodedTag } : { lang, page: "not-found", slug: path };
  }

  if (isKnownSection && !slug) return section === "articles" ? { lang, page: "articles" } : section === "tags" ? { lang, page: "tags" } : { lang, page: "section", section };

  if (isKnownSection && slug) {
    const decodedSlug = decodedSegment(slug);
    return decodedSlug ? { lang, page: "info-file", section, slug: decodedSlug } : { lang, page: "not-found", slug: path };
  }

  if (section && !slug) {
    const decodedSlug = decodedSegment(section);
    return decodedSlug ? { lang, page: "info-file", section: system, slug: decodedSlug } : { lang, page: "not-found", slug: path };
  }

  return { lang, page: "not-found", slug: path };
};
