import { ALL_TAGS, DEFAULT_PAGE_SIZE, SYSTEM_SECTION } from "@/core/config";
import type { ArticleMeta, InfoFileMeta, Lang, SectionMeta, SortBy, TagInfo, TagSortBy } from "@/core/types";

export class AppState {
  articles: ArticleMeta[] = [];
  articlesLoaded = false;
  sections: SectionMeta[] = [];
  sectionFiles = new Map<string, InfoFileMeta[]>();
  activePanel = SYSTEM_SECTION;
  activeTag = ALL_TAGS;
  tagDetail: string | null = null;
  activeArticle: ArticleMeta | null = null;
  activeInfoFile: InfoFileMeta | null = null;
  articleSearchQuery = "";
  tagSearchQuery = "";
  sortBy: SortBy = "date-desc";
  pageSize = DEFAULT_PAGE_SIZE;
  tagPageSize = DEFAULT_PAGE_SIZE;
  articlePage = 1;
  tagPage = 1;
  tagSortBy: TagSortBy = "name-asc";
  routeRenderId = 0;
  tagCountsByLang = new Map<Lang, TagInfo[]>();
  articlesByLang = new Map<Lang, ArticleMeta[]>();
  articleStats = new Map<string, { words: number; chars: number }>();
}
