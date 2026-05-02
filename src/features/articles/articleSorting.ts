import { articleTitle } from "../../services/articleService";
import type { ArticleMeta, Lang, SortBy } from "../../core/types";
export const compareArticles = (a: ArticleMeta, b: ArticleMeta, lang: Lang, sortBy: SortBy): number => { if (sortBy === "date-desc") return b.date.localeCompare(a.date); if (sortBy === "date-asc") return a.date.localeCompare(b.date); if (sortBy === "title-asc") return articleTitle(a, lang).localeCompare(articleTitle(b, lang)); return articleTitle(b, lang).localeCompare(articleTitle(a, lang)); };
export const sortArticles = (articles: readonly ArticleMeta[], lang: Lang, sortBy: SortBy): ArticleMeta[] => [...articles].sort((a, b) => compareArticles(a, b, lang, sortBy));
