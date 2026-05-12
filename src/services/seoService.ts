import { SITE_NAME, SYSTEM_SECTION } from "@/core/config";
import { updateSeoMeta } from "@/services/seoMeta";
import { articlePath, articlesPath, homePath, infoFilePath, tagPath, tagsPath } from "@/router/routePaths";
import { articleDescription, articleTitle } from "@/services/articleService";
import { DEFAULT_HREFLANG, xDefaultPath } from "@/core/languages";
import { text } from "@/ui/i18n";
import type { ArticleMeta, InfoFileMeta, Lang, Route } from "@/core/types";

type SeoUpdateArgs = {
  lang: Lang;
  title: string;
  description: string;
  indexable?: boolean;
  canonicalPath?: string;
  alternatePaths?: Partial<Record<Lang | typeof DEFAULT_HREFLANG, string>>;
  type?: "website" | "article";
  structuredData?: unknown[];
};

type RouteSeoArgs = {
  lang: Lang;
  title: string;
  description: string;
  indexable?: boolean;
  route: Route;
  activeArticle?: ArticleMeta | null;
  activeInfoFile?: InfoFileMeta | null;
  availableLanguages: readonly Lang[];
};

const withDefaultAlternate = (paths: Partial<Record<Lang, string>>): Partial<Record<Lang | typeof DEFAULT_HREFLANG, string>> => ({ ...paths, [DEFAULT_HREFLANG]: xDefaultPath(paths) });

const canonicalPathForRoute = (args: RouteSeoArgs): string => {
  if (args.activeArticle) return articlePath(args.lang, args.activeArticle.slug);
  if (args.activeInfoFile) return infoFilePath(args.lang, args.activeInfoFile.section, args.activeInfoFile.slug, args.activeInfoFile.section === SYSTEM_SECTION);
  if (args.route.page === "articles") return articlesPath(args.lang);
  if (args.route.page === "tags" && args.route.tag) return tagPath(args.lang, args.route.tag);
  if (args.route.page === "tags") return tagsPath(args.lang);
  if (args.route.page === "info-file") return infoFilePath(args.lang, args.route.section, args.route.slug, args.route.section === SYSTEM_SECTION);
  return homePath(args.lang);
};

const alternatePathsForRoute = (args: RouteSeoArgs): Partial<Record<Lang | typeof DEFAULT_HREFLANG, string>> => {
  if (args.activeArticle) {
    const paths: Partial<Record<Lang, string>> = args.activeArticle.translations ?? {};
    if (Object.keys(paths).length === 0) for (const lang of args.activeArticle.languages) paths[lang] = articlePath(lang, args.activeArticle.slug);
    return withDefaultAlternate(paths);
  }

  const paths: Partial<Record<Lang, string>> = {};
  for (const lang of args.availableLanguages) {
    if (args.route.page === "articles") paths[lang] = articlesPath(lang);
    else if (args.route.page === "tags" && args.route.tag) paths[lang] = tagPath(lang, args.route.tag);
    else if (args.route.page === "tags") paths[lang] = tagsPath(lang);
    else if (args.route.page === "info-file") paths[lang] = infoFilePath(lang, args.route.section, args.route.slug, args.route.section === SYSTEM_SECTION);
    else paths[lang] = homePath(lang);
  }
  return withDefaultAlternate(paths);
};

const breadcrumbStructuredData = (items: Array<[string, string]>): unknown => ({
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: items.map(([name, path], index) => ({ "@type": "ListItem", position: index + 1, name, item: window.location.origin + path }))
});

const structuredDataForRoute = (args: RouteSeoArgs, canonicalPath: string): unknown[] => {
  const url = window.location.origin + canonicalPath;
  if (args.activeArticle) {
    return [
      {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        headline: articleTitle(args.activeArticle, args.lang),
        description: articleDescription(args.activeArticle, args.lang),
        author: { "@type": "Person", name: SITE_NAME },
        datePublished: args.activeArticle.date,
        dateModified: args.activeArticle.date,
        mainEntityOfPage: { "@type": "WebPage", "@id": url },
        inLanguage: args.lang,
        url,
        keywords: args.activeArticle.tags.join(", "),
        isPartOf: { "@type": "Blog", name: SITE_NAME, url: window.location.origin + homePath(args.lang) }
      },
      breadcrumbStructuredData([[text(args.lang).brand, homePath(args.lang)], [text(args.lang).listTitle, articlesPath(args.lang)], [articleTitle(args.activeArticle, args.lang), articlePath(args.lang, args.activeArticle.slug)]])
    ];
  }
  return [{ "@context": "https://schema.org", "@type": "WebSite", name: SITE_NAME, description: args.description, inLanguage: args.lang, url }, breadcrumbStructuredData([[args.title, canonicalPath]])];
};

const update = (args: SeoUpdateArgs): void => updateSeoMeta(args);

export const seoService = {
  update,
  updateRoute(args: RouteSeoArgs): void {
    const indexable = args.indexable ?? true;
    const canonicalPath = canonicalPathForRoute(args);
    update({
      lang: args.lang,
      title: args.title,
      description: args.description,
      indexable,
      type: args.activeArticle ? "article" : "website",
      canonicalPath,
      alternatePaths: indexable ? alternatePathsForRoute(args) : undefined,
      structuredData: indexable ? structuredDataForRoute(args, canonicalPath) : undefined
    });
  },
  setNotFound(lang: Lang, title: string, description: string): void {
    updateSeoMeta({ lang, title, description, indexable: false, type: "website" });
  }
} as const;
