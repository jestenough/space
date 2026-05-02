import type { ArticleMeta, Lang, SortBy, TagInfo, TagSortBy } from "../core/types";
import { filterArticles } from "../features/articles/articleFilters";
import { sortArticles } from "../features/articles/articleSorting";
import { paginate } from "../features/articles/articlePagination";
import { filterTags } from "../features/tags/tagFilters";
import { sortTags } from "../features/tags/tagSorting";
export type PageModel<T> = { totalPages: number; totalItems: number; items: T[]; };
type ArticlePageArgs = { articles: ArticleMeta[]; lang: Lang; query: string; sortBy: SortBy; page: number; pageSize: number; };
type TagPageArgs = { tags: TagInfo[]; query: string; sortBy: TagSortBy; page: number; pageSize: number; };
export function buildArticlePage(args: ArticlePageArgs): PageModel<ArticleMeta> { return paginate(sortArticles(filterArticles(args.articles, args.lang, args.query), args.lang, args.sortBy), args.page, args.pageSize); }
export function buildTagPage(args: TagPageArgs): PageModel<TagInfo> { return paginate(sortTags(filterTags(args.tags, args.query), args.sortBy), args.page, args.pageSize); }
export function countTags(articles: ArticleMeta[]): TagInfo[] { const counts = new Map<string, number>(); for (const article of articles) { for (const tag of article.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1); } return Array.from(counts, ([name, count]) => ({ name, count })).sort((a, b) => a.name.localeCompare(b.name)); }
