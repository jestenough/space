import { articlePath, articlePdfPath } from "../../router/routePaths";
import type { ArticleMeta, ArticlePayload, Lang } from "../../core/types";
import { DEFAULT_LANG, isLangCode, pickLangText } from "../../core/languages";

const MAX_HTML_CACHE_ITEMS = 20;
const MAX_META_CACHE_ITEMS = 80;

let indexPromise: Promise<ArticleMeta[]> | null = null;
const htmlCache = new Map<string, Promise<string | null>>();
const metaCache = new Map<string, Promise<ArticleMeta | null>>();

export const loadArticleIndex = (): Promise<ArticleMeta[]> => {
  indexPromise ??= fetchJson("/generated/articles-index.json").then(normalizeArticleIndex);
  return indexPromise;
};

export const hasTranslation = (article: ArticleMeta, lang: Lang): boolean => {
  return article.languages.includes(lang) && Boolean(article.title[lang]) && Boolean(article.description[lang]);
};

export const articleTitle = (article: ArticleMeta, lang: Lang): string => pickLangText(article.title, lang);
export const articleDescription = (article: ArticleMeta, lang: Lang): string => pickLangText(article.description, lang);

export const articleFilePath = (slug: string, lang: Lang): string => `/generated/articles/${encodeURIComponent(slug)}.${lang}.html`;
export const articleMetaPath = (slug: string, lang: Lang): string => `/generated/articles-meta/${encodeURIComponent(slug)}.${lang}.json`;

export const loadArticle = async (slug: string, lang: Lang): Promise<ArticlePayload | null> => {
  const [meta, html] = await Promise.all([loadArticleMeta(slug, lang), loadArticleContent(slug, lang)]);
  return meta && html !== null ? { meta, html } : null;
};

export const loadArticleMeta = (slug: string, lang: Lang): Promise<ArticleMeta | null> => {
  const key = `${slug}.${lang}.json`;
  const cached = metaCache.get(key);
  if (cached) {
    metaCache.delete(key);
    metaCache.set(key, cached);
    return cached;
  }

  const request = fetchJson(articleMetaPath(slug, lang))
    .then((value) => normalizeArticleMeta(value, key))
    .catch(() => {
      metaCache.delete(key);
      return null;
    });

  setCached(metaCache, key, request, MAX_META_CACHE_ITEMS);
  return request;
};

export const loadArticleContent = (slug: string, lang: Lang): Promise<string | null> => {
  const key = `${slug}.${lang}.html`;
  const cached = htmlCache.get(key);
  if (cached) {
    htmlCache.delete(key);
    htmlCache.set(key, cached);
    return cached;
  }

  const request = fetch(articleFilePath(slug, lang), { cache: "force-cache" })
    .then((response) => response.ok ? response.text() : null)
    .catch(() => {
      htmlCache.delete(key);
      return null;
    });

  setCached(htmlCache, key, request, MAX_HTML_CACHE_ITEMS);
  return request;
};

const fetchJson = async (path: string): Promise<unknown> => {
  const response = await fetch(path, { cache: "force-cache" });
  if (!response.ok) throw new Error(`Failed to load ${path}: ${response.status}`);
  return response.json();
};

const setCached = <T>(cache: Map<string, Promise<T>>, key: string, request: Promise<T>, maxItems: number): void => {
  if (cache.has(key)) cache.delete(key);
  cache.set(key, request);
  while (cache.size > maxItems) {
    const oldestKey = cache.keys().next().value as string | undefined;
    if (!oldestKey) return;
    cache.delete(oldestKey);
  }
};

const normalizeArticleIndex = (value: unknown): ArticleMeta[] => {
  if (!Array.isArray(value)) throw new Error("Invalid article index: expected an array");
  return value.map((item, index) => normalizeArticleMeta(item, `item ${index}`));
};

const normalizeArticleMeta = (value: unknown, path: string): ArticleMeta => {
  if (!isRecord(value)) throw new Error(`Invalid article metadata at ${path}: expected object`);

  const slug = requiredString(value.slug, `${path}.slug`);
  const date = requiredString(value.date, `${path}.date`);
  const tags = requiredStringArray(value.tags, `${path}.tags`);
  const title = requiredLangRecord(value.title, `${path}.title`);
  const description = requiredLangRecord(value.description, `${path}.description`);
  const languages = requiredLangArray(value.languages, `${path}.languages`, title, description);

  return {
    slug,
    date,
    tags,
    title,
    description,
    languages,
    pdfPath: optionalString(value.pdfPath),
    canonicalPath: optionalString(value.canonicalPath),
    translations: optionalLangPathRecord(value.translations),
    prev: optionalNeighbor(value.prev),
    next: optionalNeighbor(value.next),
    wordCount: optionalNumber(value.wordCount),
    readingTime: optionalNumber(value.readingTime)
  };
};

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);

const requiredString = (value: unknown, path: string): string => {
  if (typeof value !== "string" || value.trim() === "") throw new Error(`Invalid article metadata: ${path} must be a non-empty string`);
  return value;
};

const optionalString = (value: unknown): string | undefined => typeof value === "string" && value.trim() ? value : undefined;
const optionalNumber = (value: unknown): number | undefined => typeof value === "number" && Number.isFinite(value) ? value : undefined;

const requiredStringArray = (value: unknown, path: string): string[] => {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || item.trim() === "")) {
    throw new Error(`Invalid article metadata: ${path} must be a string array`);
  }
  return [...new Set(value)];
};

const requiredLangRecord = (value: unknown, path: string): Record<string, string> => {
  if (!isRecord(value)) throw new Error(`Invalid article metadata: ${path} must be an object`);
  const result: Record<string, string> = {};
  for (const [lang, text] of Object.entries(value)) {
    if (!isLangCode(lang)) throw new Error(`Invalid article metadata: ${path}.${lang} has invalid language code`);
    result[lang] = requiredString(text, `${path}.${lang}`);
  }
  if (Object.keys(result).length === 0) throw new Error(`Invalid article metadata: ${path} must not be empty`);
  return result;
};

const requiredLangArray = (
  value: unknown,
  path: string,
  title: Record<string, string>,
  description: Record<string, string>
): Lang[] => {
  const languages = requiredStringArray(value, path);
  const valid = languages.filter(isLangCode);
  if (valid.length !== languages.length || valid.length === 0) throw new Error(`Invalid article metadata: ${path} contains invalid language codes`);
  for (const lang of valid) {
    if (!title[lang]) throw new Error(`Invalid article metadata: missing title.${lang}`);
    if (!description[lang]) throw new Error(`Invalid article metadata: missing description.${lang}`);
  }
  return valid;
};

const optionalLangPathRecord = (value: unknown): Partial<Record<Lang, string>> | undefined => {
  if (!isRecord(value)) return undefined;
  const result: Partial<Record<Lang, string>> = {};
  for (const [lang, path] of Object.entries(value)) {
    if (isLangCode(lang) && typeof path === "string" && path) result[lang] = path;
  }
  return Object.keys(result).length ? result : undefined;
};

const optionalNeighbor = (value: unknown): { title: string; path: string } | null | undefined => {
  if (value === null) return null;
  if (!isRecord(value)) return undefined;
  const title = optionalString(value.title);
  const path = optionalString(value.path);
  return title && path ? { title, path } : undefined;
};

export const articleFallbackMeta = (slug: string, lang: Lang): ArticleMeta => ({
  slug,
  date: "",
  tags: [],
  title: { [lang]: slug, [DEFAULT_LANG]: slug },
  description: { [lang]: "", [DEFAULT_LANG]: "" },
  languages: [lang],
  pdfPath: articlePdfPath(lang, slug),
  canonicalPath: articlePath(lang, slug),
  translations: { [lang]: articlePath(lang, slug) },
  prev: null,
  next: null
});
