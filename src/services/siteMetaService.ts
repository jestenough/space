import { DEFAULT_LANG, pickLangText } from "@/core/languages";
import type { Lang } from "@/core/types";

export type PageMetaKey = "home" | "articles" | "tags" | "tag" | "notFound";

type LocalizedText = Record<string, string>;
type PageMetaRecord = {
  title?: LocalizedText;
  description?: LocalizedText;
};
type SiteMeta = {
  pages?: Partial<Record<PageMetaKey, PageMetaRecord>>;
};

type PageMeta = {
  title: string;
  description: string;
};

const SITE_META_PATH = "/generated/site-meta.json";

let siteMeta: SiteMeta | null = null;
let siteMetaPromise: Promise<SiteMeta> | null = null;

const FALLBACK: Record<PageMetaKey, PageMetaRecord> = {
  home: {
    title: { [DEFAULT_LANG]: "autophany.space" },
    description: { [DEFAULT_LANG]: "Essays, notes and LaTeX articles." }
  },
  articles: {
    title: { [DEFAULT_LANG]: "Articles" },
    description: { [DEFAULT_LANG]: "All articles on autophany.space." }
  },
  tags: {
    title: { [DEFAULT_LANG]: "Tags" },
    description: { [DEFAULT_LANG]: "Article tags on autophany.space." }
  },
  tag: {
    title: { [DEFAULT_LANG]: "#{tag}" },
    description: { [DEFAULT_LANG]: "Articles tagged with {tag}." }
  },
  notFound: {
    title: { [DEFAULT_LANG]: "404 — signal lost" },
    description: { [DEFAULT_LANG]: "Page not found." }
  }
};

const fetchSiteMeta = async (): Promise<SiteMeta> => {
  try {
    const response = await fetch(SITE_META_PATH, { cache: "no-cache" });
    if (!response.ok) return {};
    const value = await response.json();
    return typeof value === "object" && value !== null && !Array.isArray(value) ? value as SiteMeta : {};
  } catch {
    return {};
  }
};

const load = async (): Promise<void> => {
  siteMetaPromise ??= fetchSiteMeta();
  siteMeta = await siteMetaPromise;
};

const getRecord = (key: PageMetaKey): PageMetaRecord => {
  return siteMeta?.pages?.[key] ?? FALLBACK[key];
};

const localized = (value: LocalizedText | undefined, lang: Lang, fallback: string): string => {
  if (!value) return fallback;
  const text = pickLangText(value, lang);
  return text.trim() || fallback;
};

const pageMeta = (key: PageMetaKey, lang: Lang): PageMeta => {
  const record = getRecord(key);
  const fallback = FALLBACK[key];

  return {
    title: localized(record.title, lang, localized(fallback.title, DEFAULT_LANG, key)),
    description: localized(record.description, lang, localized(fallback.description, DEFAULT_LANG, ""))
  };
};

const tagMeta = (lang: Lang, tag: string): PageMeta => {
  const meta = pageMeta("tag", lang);
  return {
    title: meta.title.replace(/\{tag\}/g, tag),
    description: meta.description.replace(/\{tag\}/g, tag)
  };
};

export const siteMetaService = {
  load,
  pageMeta,
  tagMeta
} as const;
