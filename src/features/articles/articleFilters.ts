import { articleDescription, articleTitle } from "@/services/articleService";
import type { ArticleMeta, Lang } from "@/core/types";
const articleSearchIndex = new WeakMap<ArticleMeta, Partial<Record<Lang, string>>>();
export const normalizeQuery = (value: string): string => value.trim().toLowerCase();
export const articleSearchText = (article: ArticleMeta, lang: Lang): string => { const cachedByLang = articleSearchIndex.get(article); const cached = cachedByLang?.[lang]; if (cached) return cached; const value = `${article.slug} ${articleTitle(article, lang)} ${articleDescription(article, lang)} ${article.tags.join(" ")}`.toLowerCase(); articleSearchIndex.set(article, { ...cachedByLang, [lang]: value }); return value; };
export const filterArticles = (articles: readonly ArticleMeta[], lang: Lang, query: string): ArticleMeta[] => { const normalizedQuery = normalizeQuery(query); return normalizedQuery ? articles.filter((article) => articleSearchText(article, lang).includes(normalizedQuery)) : [...articles]; };
