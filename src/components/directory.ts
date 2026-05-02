import type { ArticleMeta, Lang, SortBy, TagInfo, TagSortBy } from "../types";

export type PageModel<T> = {
  totalPages: number;
  totalItems: number;
  items: T[];
};

type ArticlePageArgs = {
  articles: ArticleMeta[];
  lang: Lang;
  query: string;
  sortBy: SortBy;
  page: number;
  pageSize: number;
};

type TagPageArgs = {
  tags: TagInfo[];
  query: string;
  sortBy: TagSortBy;
  page: number;
  pageSize: number;
};

const articleSearchIndex = new WeakMap<ArticleMeta, Partial<Record<Lang, string>>>();

export function buildArticlePage(args: ArticlePageArgs): PageModel<ArticleMeta> {
  const filtered = filterAndSortArticles(args.articles, args.lang, args.query, args.sortBy);
  return paginate(filtered, args.page, args.pageSize);
}

export function buildTagPage(args: TagPageArgs): PageModel<TagInfo> {
  const query = normalizeQuery(args.query);
  const filtered = query ? args.tags.filter((tag) => tag.name.toLowerCase().includes(query)) : args.tags;
  const sorted = [...filtered].sort((a, b) => compareTags(a, b, args.sortBy));
  return paginate(sorted, args.page, args.pageSize);
}

export function countTags(articles: ArticleMeta[]): TagInfo[] {
  const counts = new Map<string, number>();
  for (const article of articles) {
    for (const tag of article.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
  }
  return Array.from(counts, ([name, count]) => ({ name, count })).sort((a, b) => a.name.localeCompare(b.name));
}

const filterAndSortArticles = (articles: ArticleMeta[], lang: Lang, query: string, sortBy: SortBy): ArticleMeta[] => {
  const normalizedQuery = normalizeQuery(query);
  const filtered = normalizedQuery ? articles.filter((article) => articleSearchText(article, lang).includes(normalizedQuery)) : articles;
  return [...filtered].sort((a, b) => compareArticles(a, b, lang, sortBy));
};

const compareArticles = (a: ArticleMeta, b: ArticleMeta, lang: Lang, sortBy: SortBy): number => {
  if (sortBy === "date-desc") return b.date.localeCompare(a.date);
  if (sortBy === "date-asc") return a.date.localeCompare(b.date);
  if (sortBy === "title-asc") return a.title[lang].localeCompare(b.title[lang]);
  return b.title[lang].localeCompare(a.title[lang]);
};

const compareTags = (a: TagInfo, b: TagInfo, sortBy: TagSortBy): number => {
  if (sortBy === "name-desc") return b.name.localeCompare(a.name);
  if (sortBy === "count-desc") return b.count - a.count || a.name.localeCompare(b.name);
  if (sortBy === "count-asc") return a.count - b.count || a.name.localeCompare(b.name);
  return a.name.localeCompare(b.name);
};

const articleSearchText = (article: ArticleMeta, lang: Lang): string => {
  const cachedByLang = articleSearchIndex.get(article);
  const cached = cachedByLang?.[lang];
  if (cached) return cached;

  const value = `${article.slug} ${article.title[lang]} ${article.description[lang]} ${article.tags.join(" ")}`.toLowerCase();
  articleSearchIndex.set(article, { ...cachedByLang, [lang]: value });
  return value;
};

const normalizeQuery = (value: string): string => value.trim().toLowerCase();

const paginate = <T>(items: T[], page: number, pageSize: number): PageModel<T> => {
  const safePageSize = Number.isFinite(pageSize) && pageSize > 0 ? pageSize : 4;
  const totalPages = Math.max(1, Math.ceil(items.length / safePageSize));
  const boundedPage = Math.min(Math.max(page, 1), totalPages);
  return {
    totalPages,
    totalItems: items.length,
    items: items.slice((boundedPage - 1) * safePageSize, boundedPage * safePageSize)
  };
};
