import { articleOpenCommand, shellCommandMarkup, shellCommandText } from "@/components/shell";
import { text } from "@/ui/i18n";
import { articleDescription, articleTitle, hasTranslation, loadArticle, loadArticleIndex } from "@/services/articleService";
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
      const article = (await loadArticleIndex()).find((item) => item.slug === slug);
      if (renderId !== this.deps.currentRenderId()) return;
      if (article) {
        this.renderMissingTranslation(lang, article);
        return;
      }
      this.deps.renderNotFound(lang, slug);
      return;
    }

    const article = payload?.meta;
    if (!article) {
      this.deps.renderNotFound(lang, slug);
      return;
    }
    if (payload && !hasTranslation(article, lang)) {
      this.renderMissingTranslation(lang, article);
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
    dom.renderIndicator.innerHTML = shellCommandMarkup(articleOpenCommand(article.slug));
    document.title = `${articleTitle(article, lang)} :: ${text(lang).brand}`;
    this.deps.updateSeo(lang, articleTitle(article, lang), articleDescription(article, lang));
    this.deps.updateRightProcess(lang, { article });
    setView(ViewMode.Article);
  }

  private renderMissingTranslation(lang: Lang, article: ArticleMeta): void {
    const title = lang === "ru" ? "Пока не написано" : "Not written yet";
    const description = lang === "ru"
      ? "Этой версии пока нет, но она обязательно будет."
      : "This version does not exist yet, but it will be written.";
    const available = article.languages.join(", ");
    this.deps.setArticlesContext();
    this.deps.setActiveArticle(null);
    this.deps.applyPanelState(lang);
    this.deps.setArticleActionsVisible(false);
    articleView.renderHtml(`<section class="file-document"><h1>${title}</h1><p>${description}</p><p class="meta">available: ${available}</p></section>`);
    this.deps.renderArticleToc();
    this.deps.applyWelcomeText(title, description);
    dom.renderIndicator.innerHTML = shellCommandMarkup(shellCommandText(`test -f ~/articles/${article.slug}.${lang}.tex || echo not-translated`));
    document.title = `${title} :: ${text(lang).brand}`;
    this.deps.updateSeo(lang, title, description, false);
    this.deps.updateRightProcess(lang);
    setView(ViewMode.Article);
  }
}
