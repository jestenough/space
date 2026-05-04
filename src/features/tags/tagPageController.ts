import { ALL_TAGS } from "../../core/config";
import { buildArticlePage, buildTagPage } from "../../components/directory";
import { text } from "../../ui/i18n";
import { siteMetaService } from "../../services/siteMetaService";
import type { ArticleMeta, Lang, SortBy, TagInfo, TagSortBy } from "../../core/types";
import { setView } from "../../ui/view";
import { ViewMode } from "../../core/enums";
import { listView } from "../../ui/views/listView";

export type TagPageControllerDeps = {
  articlesForLang: (lang: Lang) => ArticleMeta[];
  tagsForLang: (lang: Lang) => TagInfo[];
  getTagDetail: () => string | null;
  getActiveTag: () => string;
  getArticleQuery: () => string;
  getTagQuery: () => string;
  getArticleSortBy: () => SortBy;
  getTagSortBy: () => TagSortBy;
  getArticlePage: () => number;
  setArticlePage: (page: number) => void;
  getTagPage: () => number;
  setTagPage: (page: number) => void;
  getArticlePageSize: () => number;
  getTagPageSize: () => number;
  applyPanelState: (lang: Lang) => void;
  renderNotFound: (lang: Lang, slug?: string) => void;
  updateSeo: (lang: Lang, title: string, description: string, indexable?: boolean) => void;
  updateRightProcess: (lang: Lang, context?: { tag?: string; matches?: number }) => void;
};

export class TagPageController {
  constructor(private readonly deps: TagPageControllerDeps) {}

  renderIndex(lang: Lang): void {
    const ui = text(lang);
    this.deps.applyPanelState(lang);
    const page = buildTagPage({
      tags: this.deps.tagsForLang(lang),
      query: this.deps.getTagQuery(),
      sortBy: this.deps.getTagSortBy(),
      page: this.deps.getTagPage(),
      pageSize: this.deps.getTagPageSize()
    });
    const currentPage = Math.min(this.deps.getTagPage(), page.totalPages);
    this.deps.setTagPage(currentPage);
    listView.renderTags(lang, page, currentPage, this.deps.getActiveTag(), ui.tagsHeadline);
    const meta = siteMetaService.pageMeta("tags", lang);
    document.title = `${meta.title} :: ${ui.brand}`;
    this.deps.updateSeo(lang, meta.title, meta.description);
    this.deps.updateRightProcess(lang, { matches: page.totalItems });
    setView(ViewMode.List);
  }

  renderDetail(lang: Lang): void {
    const ui = text(lang);
    this.deps.applyPanelState(lang);
    const tag = this.deps.getTagDetail();
    const tagArticles = this.deps.articlesForLang(lang).filter((article) => article.tags.includes(tag ?? ALL_TAGS));
    if (!tag || tagArticles.length === 0) {
      this.deps.renderNotFound(lang, tag ? `tags/${tag}` : undefined);
      return;
    }
    const page = buildArticlePage({
      articles: tagArticles,
      lang,
      query: this.deps.getArticleQuery(),
      sortBy: this.deps.getArticleSortBy(),
      page: this.deps.getArticlePage(),
      pageSize: this.deps.getArticlePageSize()
    });
    const currentPage = Math.min(this.deps.getArticlePage(), page.totalPages);
    this.deps.setArticlePage(currentPage);
    listView.renderArticles(lang, page, currentPage, `#${tag}`);
    const meta = siteMetaService.tagMeta(lang, tag);
    document.title = `${meta.title} :: ${ui.brand}`;
    this.deps.updateSeo(lang, meta.title, meta.description);
    this.deps.updateRightProcess(lang, { tag, matches: page.totalItems });
    setView(ViewMode.List);
  }
}
