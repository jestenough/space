import { buildArticlePage } from "@/components/directory";
import { text } from "@/ui/i18n";
import { siteMetaService } from "@/services/siteMetaService";
import type { ArticleMeta, Lang, SortBy } from "@/core/types";
import { setView } from "@/ui/view";
import { ViewMode } from "@/core/enums";
import { listView } from "@/ui/views/listView";

export type ArticleListControllerDeps = {
  articlesForLang: (lang: Lang) => ArticleMeta[];
  getQuery: () => string;
  getSortBy: () => SortBy;
  getPage: () => number;
  setPage: (page: number) => void;
  getPageSize: () => number;
  applyPanelState: (lang: Lang) => void;
  updateSeo: (lang: Lang, title: string, description: string, indexable?: boolean) => void;
  updateRightProcess: (lang: Lang, context?: { matches?: number }) => void;
};

export class ArticleListController {
  constructor(private readonly deps: ArticleListControllerDeps) {}

  render(lang: Lang): void {
    const ui = text(lang);
    this.deps.applyPanelState(lang);
    const page = buildArticlePage({
      articles: this.deps.articlesForLang(lang),
      lang,
      query: this.deps.getQuery(),
      sortBy: this.deps.getSortBy(),
      page: this.deps.getPage(),
      pageSize: this.deps.getPageSize()
    });
    const currentPage = Math.min(this.deps.getPage(), page.totalPages);
    this.deps.setPage(currentPage);
    listView.renderArticles(lang, page, currentPage, ui.listTitle);
    const meta = siteMetaService.pageMeta("articles", lang);
    document.title = `${meta.title} :: ${ui.brand}`;
    this.deps.updateSeo(lang, meta.title, meta.description);
    this.deps.updateRightProcess(lang, { matches: page.totalItems });
    setView(ViewMode.List);
  }
}
