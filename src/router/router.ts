import { DEFAULT_LANG, isLangCode, normalizeLang } from "@/core/languages";
import { INFO_FILES, toRouteSlug } from "@/features/info/infoFiles";
import type { Lang, Route } from "@/core/types";
import { safeDecodeURIComponent } from "@/core/url";

const INFO_FILE_ROUTE_SLUGS = new Set(
  INFO_FILES.flatMap((file) => [file.slug.toLowerCase(), toRouteSlug(file.slug)])
);
const ROUTE_SECTION_ARTICLES = "articles";
const ROUTE_SECTION_TAGS = "tags";

export const toLang = (value: string | undefined): Lang => normalizeLang(value);

const decodedSegment = (value: string | undefined): string | null => {
  if (value === undefined) return null;
  return safeDecodeURIComponent(value);
};

export const parseRoute = (): Route => {
  const path = window.location.pathname.replace(/^\/+|\/+$/g, "");
  if (!path) return { lang: DEFAULT_LANG, page: "home", panel: "home" };

  const [langCandidate, section, slug, extra] = path.split("/");
  if (!isLangCode(langCandidate)) return { lang: DEFAULT_LANG, page: "not-found", slug: path };

  const lang = normalizeLang(langCandidate);
  if (extra) return { lang, page: "not-found", slug: path };
  if (section === undefined) return { lang, page: "home", panel: "home" };

  if (section === ROUTE_SECTION_ARTICLES && slug) {
    const decodedSlug = decodedSegment(slug);
    return decodedSlug ? { lang, page: "article", slug: decodedSlug } : { lang, page: "not-found", slug: path };
  }

  if (section === ROUTE_SECTION_ARTICLES) return { lang, page: "articles" };

  if (section === ROUTE_SECTION_TAGS && slug) {
    const decodedTag = decodedSegment(slug);
    return decodedTag ? { lang, page: "tags", tag: decodedTag } : { lang, page: "not-found", slug: path };
  }

  if (section === ROUTE_SECTION_TAGS) return { lang, page: "tags" };

  if (section && !slug) {
    const decodedSection = decodedSegment(section);
    if (!decodedSection) return { lang, page: "not-found", slug: path };

    const normalized = decodedSection.trim().toLowerCase();
    if (INFO_FILE_ROUTE_SLUGS.has(normalized)) return { lang, page: "info-file", slug: decodedSection };
    return { lang, page: "not-found", slug: path };
  }

  return { lang, page: "not-found", slug: path };
};

export const navigateHome = (lang: Lang): void => {
  window.location.href = `/${lang}`;
};
