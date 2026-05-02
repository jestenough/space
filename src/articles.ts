import type { ArticleMeta, Lang } from "./types";
import { LANG_EN, LANG_RU } from "./config";

const MAX_HTML_CACHE_ITEMS = 20;

let indexPromise: Promise<ArticleMeta[]> | null = null;
const htmlCache = new Map<string, Promise<string | null>>();

export function loadArticleIndex(): Promise<ArticleMeta[]> {
  indexPromise ??= fetch("/generated/articles-index.json", { cache: "force-cache" }).then(async (response) => {
    if (!response.ok) throw new Error("Failed to load article index");
    return normalizeArticleIndex(await response.json());
  });
  return indexPromise;
}

export function hasTranslation(article: ArticleMeta, lang: Lang): boolean {
  return article.languages.includes(lang);
}

export function articleFilePath(slug: string, lang: Lang): string {
  return `/generated/articles/${encodeURIComponent(slug)}.${lang}.html`;
}

export function loadArticleContent(slug: string, lang: Lang): Promise<string | null> {
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

  setCachedArticleHtml(key, request);
  return request;
}

const setCachedArticleHtml = (key: string, request: Promise<string | null>): void => {
  if (htmlCache.has(key)) htmlCache.delete(key);
  htmlCache.set(key, request);

  while (htmlCache.size > MAX_HTML_CACHE_ITEMS) {
    const oldestKey = htmlCache.keys().next().value as string | undefined;
    if (!oldestKey) return;
    htmlCache.delete(oldestKey);
  }
};

const normalizeArticleIndex = (value: unknown): ArticleMeta[] => {
  if (!Array.isArray(value)) throw new Error("Invalid article index: expected an array");
  return value.map((item, index) => normalizeArticleMeta(item, index));
};

const normalizeArticleMeta = (value: unknown, index: number): ArticleMeta => {
  if (!isRecord(value)) throw new Error(`Invalid article index item at ${index}: expected object`);

  const slug = requiredString(value.slug, `item ${index}.slug`);
  const date = requiredString(value.date, `item ${index}.date`);
  const tags = requiredStringArray(value.tags, `item ${index}.tags`);
  const title = requiredLangRecord(value.title, `item ${index}.title`);
  const description = requiredLangRecord(value.description, `item ${index}.description`);
  const languages = requiredLangArray(value.languages, `item ${index}.languages`);

  return { slug, date, tags, title, description, languages };
};

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);

const requiredString = (value: unknown, path: string): string => {
  if (typeof value !== "string" || value.trim() === "") throw new Error(`Invalid article index: ${path} must be a non-empty string`);
  return value;
};

const requiredStringArray = (value: unknown, path: string): string[] => {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || item.trim() === "")) {
    throw new Error(`Invalid article index: ${path} must be a string array`);
  }
  return value;
};

const requiredLangRecord = (value: unknown, path: string): Record<Lang, string> => {
  if (!isRecord(value)) throw new Error(`Invalid article index: ${path} must be an object`);
  return {
    ru: requiredString(value.ru, `${path}.ru`),
    en: requiredString(value.en, `${path}.en`)
  };
};

const requiredLangArray = (value: unknown, path: string): Lang[] => {
  const languages = requiredStringArray(value, path);
  const valid = languages.filter((lang): lang is Lang => lang === LANG_RU || lang === LANG_EN);
  if (valid.length !== languages.length || valid.length === 0) {
    throw new Error(`Invalid article index: ${path} must contain only ru/en`);
  }
  return [...new Set(valid)];
};
