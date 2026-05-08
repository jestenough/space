import type { ArticleMeta, ArticlePayload, Lang } from "@/core/types";
import { isLangCode, pickLangText } from "@/core/languages";
import { fetchGeneratedJson, fetchGeneratedText, PromiseLruCache } from "@/services/generatedAssets";
import { generatedFileHtmlPath, generatedSectionIndexPath } from "@/services/generatedPaths";

const MAX_HTML_CACHE_ITEMS = 20;

let indexPromise: Promise<ArticleMeta[]> | null = null;
const htmlCache = new PromiseLruCache<string>(MAX_HTML_CACHE_ITEMS);

export const loadArticleIndex = (): Promise<ArticleMeta[]> => {
  indexPromise ??= fetchGeneratedJson(generatedSectionIndexPath("articles")).then(normalizeArticleIndex);
  return indexPromise;
};

export const hasTranslation = (article: ArticleMeta, lang: Lang): boolean => {
  return article.languages.includes(lang) && Boolean(article.title[lang]) && Boolean(article.description[lang]);
};

export const articleTitle = (article: ArticleMeta, lang: Lang): string => pickLangText(article.title, lang);
export const articleDescription = (article: ArticleMeta, lang: Lang): string => pickLangText(article.description, lang);

export const loadArticle = async (slug: string, lang: Lang): Promise<ArticlePayload | null> => {
  const articles = await loadArticleIndex();
  const meta = articles.find((article) => article.slug === slug) ?? null;
  if (!meta || !hasTranslation(meta, lang)) return null;
  const html = await loadArticleContent(slug, lang);
  return { meta, html };
};

export const loadArticleContent = (slug: string, lang: Lang): Promise<string> => {
  const key = `${slug}.${lang}.html`;
  const cached = htmlCache.get(key);
  if (cached) return cached;

  const request = fetchGeneratedText(generatedFileHtmlPath("articles", slug, lang));

  htmlCache.set(key, request);
  return request;
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
