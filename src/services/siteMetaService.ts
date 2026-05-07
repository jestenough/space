import { pickLangText } from "@/core/languages";
import type { Lang } from "@/core/types";
import { fetchGeneratedJson } from "@/services/generatedAssets";
import { generatedSiteMetaPath } from "@/services/generatedPaths";

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

const SITE_META_PATH = generatedSiteMetaPath();

let siteMeta: SiteMeta | null = null;
let siteMetaPromise: Promise<SiteMeta> | null = null;

const fetchSiteMeta = async (): Promise<SiteMeta> => {
  const value = await fetchGeneratedJson(SITE_META_PATH);
  if (typeof value !== "object" || value === null || Array.isArray(value)) throw new Error(`Invalid site meta: ${SITE_META_PATH}`);
  return value as SiteMeta;
};

const load = async (): Promise<void> => {
  siteMetaPromise ??= fetchSiteMeta();
  siteMeta = await siteMetaPromise;
};

const getRecord = (key: PageMetaKey): PageMetaRecord => {
  const record = siteMeta?.pages?.[key];
  if (!record) throw new Error(`Missing site meta page: ${key}`);
  return record;
};

const localized = (value: LocalizedText | undefined, lang: Lang, path: string): string => {
  if (!value) throw new Error(`Missing localized site meta: ${path}`);
  const text = pickLangText(value, lang);
  if (!text.trim()) throw new Error(`Missing localized site meta: ${path}.${lang}`);
  return text.trim();
};

const pageMeta = (key: PageMetaKey, lang: Lang): PageMeta => {
  const record = getRecord(key);

  return {
    title: localized(record.title, lang, `${key}.title`),
    description: localized(record.description, lang, `${key}.description`)
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
