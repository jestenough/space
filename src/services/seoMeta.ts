import type { Lang } from "../core/types";
import { DEFAULT_HREFLANG, formatOgLocale } from "../core/languages";

type SeoArgs = {
  lang: Lang;
  title: string;
  description: string;
  indexable?: boolean;
  canonicalPath?: string;
  alternatePaths?: Partial<Record<Lang | typeof DEFAULT_HREFLANG, string>>;
  type?: "website" | "article";
  structuredData?: unknown[];
};

export const updateSeoMeta = (args: SeoArgs): void => {
  const description = args.description.replace(/\s+/g, " ").trim().slice(0, 155);
  const canonicalUrl = window.location.origin + (args.canonicalPath ?? window.location.pathname);
  document.documentElement.lang = args.lang;
  ensureMeta('meta[name="description"]', { name: "description" }).content = description;
  ensureMeta('meta[name="robots"]', { name: "robots" }).content = args.indexable === false ? "noindex,nofollow" : "index,follow";
  ensureMeta('meta[property="og:title"]', { property: "og:title" }).content = args.title;
  ensureMeta('meta[property="og:description"]', { property: "og:description" }).content = description;
  ensureMeta('meta[property="og:type"]', { property: "og:type" }).content = args.type ?? "website";
  ensureMeta('meta[property="og:url"]', { property: "og:url" }).content = canonicalUrl;
  ensureMeta('meta[property="og:locale"]', { property: "og:locale" }).content = formatOgLocale(args.lang);
  ensureMeta('meta[name="twitter:card"]', { name: "twitter:card" }).content = "summary";
  ensureMeta('meta[name="twitter:title"]', { name: "twitter:title" }).content = args.title;
  ensureMeta('meta[name="twitter:description"]', { name: "twitter:description" }).content = description;

  let canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if (!canonical) {
    canonical = document.createElement("link");
    canonical.rel = "canonical";
    document.head.append(canonical);
  }
  canonical.href = canonicalUrl;

  document.head.querySelectorAll<HTMLLinkElement>('link[rel="alternate"][data-managed-seo="true"]').forEach((node) => node.remove());
  for (const [hreflang, path] of Object.entries(args.alternatePaths ?? {})) {
    if (!path) continue;
    const link = document.createElement("link");
    link.rel = "alternate";
    link.hreflang = hreflang;
    link.href = window.location.origin + path;
    link.dataset.managedSeo = "true";
    document.head.append(link);
  }

  document.getElementById("structured-data")?.remove();
  if (args.structuredData?.length) {
    const script = document.createElement("script");
    script.id = "structured-data";
    script.type = "application/ld+json";
    script.textContent = JSON.stringify(args.structuredData.length === 1 ? args.structuredData[0] : args.structuredData);
    document.head.append(script);
  }
};

const ensureMeta = (selector: string, attrs: Record<string, string>): HTMLMetaElement => {
  let meta = document.head.querySelector<HTMLMetaElement>(selector);
  if (!meta) {
    meta = document.createElement("meta");
    for (const [key, value] of Object.entries(attrs)) meta.setAttribute(key, value);
    document.head.append(meta);
  }
  return meta;
};
