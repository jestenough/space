import { articleOpenCommand } from "@/components/shell";
import { text } from "@/ui/i18n";
import { articleDescription, articleFallbackMeta, articleTitle, hasTranslation, loadArticle } from "@/services/articleService";
import type { ArticleMeta, Lang } from "@/core/types";
import { setView } from "@/ui/view";
import { ViewMode } from "@/core/enums";
import { articleView } from "@/ui/views/articleView";
import { dom } from "@/ui/dom";

type ArticleRenderContext = { article?: ArticleMeta; matches?: number };

export type ArticlePageControllerDeps = {
  currentRenderId: () => number;
  renderNotFound: (lang: Lang, slug?: string) => void;
  setArticlesContext: () => void;
  setActiveArticle: (article: ArticleMeta | null) => void;
  applyPanelState: (lang: Lang) => void;
  renderArticleToc: () => void;
  setArticleActionsVisible: (isVisible: boolean) => void;
  applyWelcomeText: (title: string, lead: string, body?: string) => void;
  cacheCurrentArticleStats: (lang: Lang, slug: string) => void;
  updateSeo: (lang: Lang, title: string, description: string, indexable?: boolean) => void;
  updateRightProcess: (lang: Lang, context?: ArticleRenderContext) => void;
};

export class ArticlePageController {
  constructor(private readonly deps: ArticlePageControllerDeps) {}

  async render(lang: Lang, slug: string, renderId: number): Promise<void> {
    const prerenderedHtml = dom.articleContent.querySelector("article") ? dom.articleContent.innerHTML : null;
    const payload = await loadArticle(slug, lang);
    if (renderId !== this.deps.currentRenderId()) return;
    if (!payload && !prerenderedHtml) {
      this.deps.renderNotFound(lang, slug);
      return;
    }

    const article = payload?.meta ?? articleFallbackMeta(slug, lang);
    if (payload && !hasTranslation(article, lang)) {
      this.deps.renderNotFound(lang, slug);
      return;
    }

    this.deps.setArticlesContext();
    this.deps.setActiveArticle(article);
    this.deps.applyPanelState(lang);
    if (payload) articleView.renderHtml(payload.html);
    else if (prerenderedHtml) dom.articleContent.innerHTML = prerenderedHtml;
    articleView.finalize(lang, article);
    this.deps.cacheCurrentArticleStats(lang, slug);
    this.deps.renderArticleToc();
    this.deps.setArticleActionsVisible(true);
    dom.downloadPdfBtn.textContent = "pdf";
    dom.editArticleBtn.textContent = "edit";
    dom.zenModeBtn.textContent = "zen";
    this.deps.applyWelcomeText(articleTitle(article, lang), articleDescription(article, lang));
    dom.renderIndicator.textContent = articleOpenCommand(article.slug);
    document.title = `${articleTitle(article, lang)} :: ${text(lang).brand}`;
    this.deps.updateSeo(lang, articleTitle(article, lang), articleDescription(article, lang));
    this.deps.updateRightProcess(lang, { article });
    setView(ViewMode.Article);
  }
}
