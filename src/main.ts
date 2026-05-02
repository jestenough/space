import "./styles/index.css";
import { ALL_TAGS, DEFAULT_HREFLANG, DEFAULT_PAGE_SIZE, GITHUB_EDIT_BASE, LANG_EN, LANG_RU, PAGE_SIZE_OPTIONS, ROUTE_PREFIX } from "./config";
import { hasTranslation, loadArticleContent, loadArticleIndex } from "./articles";
import { panelInfo } from "./components/panels";
import { controls } from "./components/controls";
import { buildArticlePage, buildTagPage, countTags, type PageModel } from "./components/directory";
import { TocController } from "./components/toc";
import { findInfoFile, INFO_FILES, renderInfoFileHtml } from "./infoFiles";
import { articleOpenCommand, headerCommand, infoFileOpenCommand, processSnapshotHtml, sidebarCommand } from "./components/shell";
import { dom } from "./dom";
import { applyUiText, text } from "./i18n";
import { parseRoute, toLang } from "./router";
import { safeDecodeURIComponent } from "./url";
import { articlePath, articlePdfPath, articlesPath, homePath, infoFilePath, tagPath, tagsPath } from "./routePaths";
import { updateSeoMeta } from "./seo";
import { localGet, localSet, sessionGet, sessionRemove, sessionSet } from "./storage";
import { countTextStats } from "./textStats";
import { applyTheme } from "./theme";
import type { ArticleMeta, InfoFileMeta, Lang, Route, SortBy, TagInfo, TagSortBy } from "./types";
import { renderArticleContent, renderArticleList, renderInfoFileList, renderTagIndex, setView } from "./view";

type RenderContext = { article?: ArticleMeta; infoFile?: InfoFileMeta; tag?: string; matches?: number };
type TagPageModel = PageModel<TagInfo>;

const MAX_ARTICLE_STATS_CACHE = 80;

const PANEL_HOME = "home" as const;
const PANEL_ARTICLES = "articles" as const;
const PANEL_TAGS = "tags" as const;
const PAGE_ARTICLE = "article" as const;
const PAGE_ARTICLES = "articles" as const;
const PAGE_TAGS = "tags" as const;
const PAGE_INFO_FILE = "info-file" as const;
const PAGE_NOT_FOUND = "not-found" as const;
const VIEW_LIST = "list" as const;
const VIEW_ARTICLE = "article" as const;
const VIEW_ERROR = "error" as const;

class BlogApp {
  private articles: ArticleMeta[] = [];
  private articlesLoaded = false;
  private activePanel: "home" | "articles" | "tags" = PANEL_HOME;
  private activeTag = ALL_TAGS;
  private tagDetail: string | null = null;
  private activeArticle: ArticleMeta | null = null;
  private activeInfoFile: InfoFileMeta | null = null;
  private articleSearchQuery = "";
  private tagSearchQuery = "";
  private sortBy: SortBy = "date-desc";
  private pageSize = DEFAULT_PAGE_SIZE;
  private tagPageSize = DEFAULT_PAGE_SIZE;
  private articlePage = 1;
  private tagPage = 1;
  private tagSortBy: TagSortBy = "name-asc";
  private renderFrame = 0;
  private headerFrame = 0;
  private tocScrollFrame = 0;
  private routeRenderId = 0;
  private currentArticleReadKey: string | null = null;
  private zenTopHover = false;
  private tagCountsByLang = new Map<Lang, TagInfo[]>();
  private articlesByLang = new Map<Lang, ArticleMeta[]>();
  private articleStats = new Map<string, { words: number; chars: number }>();
  private searchRenderTimer: number | null = null;
  private tocController = new TocController();

  async init(): Promise<void> {
    applyTheme(localGet("theme") ?? "system");
    this.bindEvents();
    await this.renderRoute({ resetScroll: false });
  }

  private bindEvents(): void {
    document.addEventListener("click", (event) => this.handleDocumentClick(event));
    window.addEventListener("popstate", () => void this.renderRoute({ resetScroll: false }));
    window.addEventListener("resize", () => this.scheduleHeaderUpdate());
    document.addEventListener("keydown", (event) => this.handleKeydown(event));
    document.addEventListener("mousemove", (event) => this.handleZenMousemove(event));
    document.addEventListener("copy", (event) => this.handleArticleCopy(event));

    dom.langSwitcher.addEventListener("change", () => this.changeLanguage());
    dom.themeSwitcher.addEventListener("change", () => applyTheme(dom.themeSwitcher.value));
    this.bindSearchInput(controls.articles.searchInput, {
      get: () => this.articleSearchQuery,
      set: (value) => {
        this.articleSearchQuery = value;
        this.articlePage = 1;
      }
    });
    this.bindSearchInput(controls.tags.searchInput, {
      get: () => this.tagSearchQuery,
      set: (value) => {
        this.tagSearchQuery = value;
        this.tagPage = 1;
      }
    });

    this.bindSelectReset(controls.articles.sortSelect, () => {
      this.sortBy = controls.articles.sortSelect.value as SortBy;
      this.articlePage = 1;
    });
    this.bindSelectReset(controls.articles.sizeSelect, () => {
      this.pageSize = this.normalizePageSize(Number.parseInt(controls.articles.sizeSelect.value, 10));
      this.articlePage = 1;
    });
    this.bindSelectReset(controls.tags.sortSelect, () => {
      this.tagSortBy = controls.tags.sortSelect.value as TagSortBy;
      this.tagPage = 1;
    });
    this.bindSelectReset(controls.tags.sizeSelect, () => {
      this.tagPageSize = this.normalizePageSize(Number.parseInt(controls.tags.sizeSelect.value, 10));
      this.tagPage = 1;
    });

    this.bindPagerButton(controls.articles.pagePrev, () => {
      if (this.articlePage > 1) this.articlePage -= 1;
      return this.articlePage;
    });
    this.bindPagerButton(controls.articles.pageNext, () => {
      this.articlePage += 1;
      return this.articlePage;
    });
    this.bindPagerButton(controls.tags.pagePrev, () => {
      if (this.tagPage > 1) this.tagPage -= 1;
      return this.tagPage;
    });
    this.bindPagerButton(controls.tags.pageNext, () => {
      this.tagPage += 1;
      return this.tagPage;
    });

    dom.downloadPdfBtn.addEventListener("click", () => this.openCurrentArticlePdf());
    dom.editArticleBtn.addEventListener("click", () => this.openCurrentArticleEditor());
    dom.zenModeBtn.addEventListener("click", () => this.enterZenMode());
    dom.zenExitBtn.addEventListener("click", () => this.exitZenMode());
  }

  private bindSearchInput(
    input: HTMLInputElement,
    handlers: { get: () => string; set: (value: string) => void }
  ): void {
    input.addEventListener("input", () => {
      const next = input.value.trim().toLowerCase();
      if (next === handlers.get()) return;
      handlers.set(next);
      this.setPageParam(1, true);
      this.scheduleSearchRender();
    });
  }

  private bindSelectReset(select: HTMLSelectElement, apply: () => void): void {
    select.addEventListener("change", () => {
      apply();
      this.setPageParam(1, true);
      this.scheduleRender();
    });
  }

  private bindPagerButton(button: HTMLButtonElement, update: () => number): void {
    button.addEventListener("click", () => {
      const page = update();
      this.setPageParam(page);
      void this.renderRoute({ resetScroll: false });
    });
  }

  private handleDocumentClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    const anchor = target.closest("a[href]") as HTMLAnchorElement | null;
    if (!anchor) {
      const heading = target.closest<HTMLElement>("#article-content h1[id], #article-content h2[id], #article-content h3[id], #article-content h4[id], #article-content h5[id], #article-content h6[id]");
      if (!heading?.id) return;
      this.openHeadingAnchor(heading.id, true);
      return;
    }

    const url = new URL(anchor.href, window.location.origin);
    const isHashOnly = url.pathname === window.location.pathname && Boolean(url.hash);
    if (isHashOnly) {
      event.preventDefault();
      const headingId = safeDecodeURIComponent(url.hash.slice(1));
      if (headingId) this.openHeadingAnchor(headingId, true);
      return;
    }
    if (anchor.target || anchor.hasAttribute("download") || url.pathname.endsWith(".pdf")) return;
    if (url.origin !== window.location.origin || !ROUTE_PREFIX.test(url.pathname)) return;

    event.preventDefault();
    if (anchor.dataset.articleSlug) sessionSet("article-back-path", this.currentListPath(parseRoute().lang));
    this.navigateTo(url.pathname + url.search + url.hash);
  }

  private handleKeydown(event: KeyboardEvent): void {
    const route = parseRoute();
    const key = event.key.toLowerCase();
    const target = event.target as HTMLElement | null;
    const isTyping = target?.matches("input, textarea, select, [contenteditable='true']") ?? false;

    if (!isTyping && (key === "1" || key === "a")) this.navigateTo(articlesPath(route.lang));
    if (!isTyping && (key === "2" || key === "t")) this.navigateTo(tagsPath(route.lang));
    if (!isTyping && (key === "3" || key === "h")) this.navigateTo(homePath(route.lang));
    if (!isTyping && key === "4") this.cycleTheme();
    if (event.key === "/" && !isTyping) {
      event.preventDefault();
      if (this.activePanel === PANEL_TAGS && !this.tagDetail) controls.tags.searchInput.focus();
      else controls.articles.searchInput.focus();
    }
    if (event.key === "Escape") {
      this.exitZenMode();
      controls.articles.searchInput.blur();
      controls.tags.searchInput.blur();
    }
  }

  private handleZenMousemove(event: MouseEvent): void {
    if (!document.body.classList.contains("zen-mode")) return;
    const nextHover = event.clientY < 76;
    if (nextHover === this.zenTopHover) return;
    this.zenTopHover = nextHover;
    document.body.classList.toggle("zen-top-hover", nextHover);
  }

  private handleArticleCopy(event: ClipboardEvent): void {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;
    const anchorNode = selection.anchorNode;
    const focusNode = selection.focusNode;
    const insideArticle = (node: Node | null): boolean => Boolean(node && dom.articleContent.contains(node.nodeType === Node.TEXT_NODE ? node.parentElement : node));
    if (!insideArticle(anchorNode) && !insideArticle(focusNode)) return;

    const textValue = selection.toString();
    if (!textValue) return;
    event.clipboardData?.setData("text/plain", textValue);
    event.preventDefault();
  }

  private navigateTo(path: string): void {
    if (path === window.location.pathname + window.location.search + window.location.hash) return;
    this.cancelSearchRender();
    window.history.pushState({}, "", path);
    void this.renderRoute({ resetScroll: true });
  }

  private scheduleRender(): void {
    cancelAnimationFrame(this.renderFrame);
    this.renderFrame = requestAnimationFrame(() => void this.renderRoute({ resetScroll: false }));
  }

  private cancelSearchRender(): void {
    if (this.searchRenderTimer === null) return;
    window.clearTimeout(this.searchRenderTimer);
    this.searchRenderTimer = null;
  }

  private scheduleSearchRender(): void {
    if (this.searchRenderTimer !== null) window.clearTimeout(this.searchRenderTimer);
    this.searchRenderTimer = window.setTimeout(() => {
      this.searchRenderTimer = null;
      this.scheduleRender();
    }, 120);
  }

  private scheduleHeaderUpdate(): void {
    cancelAnimationFrame(this.headerFrame);
    this.headerFrame = requestAnimationFrame(() => {
      dom.renderIndicator.textContent = this.currentHeaderCommand();
    });
  }

  private changeLanguage(): void {
    const targetLang = toLang(dom.langSwitcher.value);
    const route = parseRoute();
    if (route.page === PAGE_ARTICLE && this.activeArticle && hasTranslation(this.activeArticle, targetLang)) {
      this.navigateTo(articlePath(targetLang, this.activeArticle.slug));
      return;
    }
    if (route.page === PAGE_INFO_FILE) {
      this.navigateTo(infoFilePath(targetLang, route.slug));
      return;
    }
    if (route.page === PAGE_TAGS && route.tag) {
      this.navigateTo(tagPath(targetLang, route.tag));
      return;
    }
    this.navigateTo(route.page === PAGE_ARTICLES ? articlesPath(targetLang) : route.page === PAGE_TAGS ? tagsPath(targetLang) : homePath(targetLang));
  }

  private cycleTheme(): void {
    const order = ["reading", "light", "system", "dark"] as const;
    const current = dom.themeSwitcher.value;
    const idx = Math.max(0, order.indexOf(current as (typeof order)[number]));
    const next = order[(idx + 1) % order.length];
    dom.themeSwitcher.value = next;
    applyTheme(next);
  }

  private normalizePageSize(value: number): number {
    return PAGE_SIZE_OPTIONS.includes(value as (typeof PAGE_SIZE_OPTIONS)[number]) ? value : DEFAULT_PAGE_SIZE;
  }

  private renderHome(lang: Lang): void {
    const ui = text(lang);
    const articlesByLang = this.articlesForLang(lang);
    this.applyPanelState(lang);

    if (this.activePanel === PANEL_HOME) {
      renderInfoFileList(lang, INFO_FILES);
      document.title = "root :: " + ui.brand;
      this.updateSeo(lang, ui.welcomeTitle, ui.welcomeBody);
      this.updateRightProcess(lang);
      setView(VIEW_LIST);
      return;
    }

    if (this.activePanel === PANEL_ARTICLES) {
      const page = buildArticlePage({
        articles: articlesByLang,
        lang,
        query: this.articleSearchQuery,
        sortBy: this.sortBy,
        page: this.articlePage,
        pageSize: this.pageSize
      });
      this.articlePage = Math.min(this.articlePage, page.totalPages);
      this.renderArticleDirectory(lang, page, text(lang).listTitle);
      document.title = `${ui.listTitle} :: ${ui.brand}`;
      this.updateSeo(lang, ui.listTitle, lang === "ru" ? "Каталог статей autophany.space: LaTeX, заметки, тэги и терминальная навигация." : "autophany.space article catalog: LaTeX, notes, tags, and terminal navigation.");
      this.updateRightProcess(lang, { matches: page.totalItems });
      setView(VIEW_LIST);
      return;
    }

    if (!this.tagDetail) {
      const tags = buildTagPage({
        tags: this.tagsForLang(lang),
        query: this.tagSearchQuery,
        sortBy: this.tagSortBy,
        page: this.tagPage,
        pageSize: this.tagPageSize
      });
      this.tagPage = Math.min(this.tagPage, tags.totalPages);
      renderTagIndex(lang, tags.items, this.activeTag);
      this.renderTagPager(tags);
      dom.articleList.replaceChildren();
      dom.listTitle.textContent = ui.tagsHeadline;
      dom.tagsSubtitle.textContent = "";
      controls.articles.pageInfo.textContent = "";
      controls.articles.pagePrev.disabled = true;
      controls.articles.pageNext.disabled = true;
      document.title = `${ui.tagsHeadline} :: ${ui.brand}`;
      this.updateSeo(lang, ui.tagsHeadline, lang === "ru" ? "Индекс тэгов и тематических подборок autophany.space." : "Tag index and topical clusters in autophany.space.");
      this.updateRightProcess(lang, { matches: tags.totalItems });
      setView(VIEW_LIST);
      return;
    }

    const tagArticles = articlesByLang.filter((article) => article.tags.includes(this.tagDetail ?? ALL_TAGS));
    if (tagArticles.length === 0) {
      this.renderNotFound(lang, this.tagDetail ? "tags/" + this.tagDetail : undefined);
      return;
    }
    const page = buildArticlePage({
      articles: tagArticles,
      lang,
      query: this.articleSearchQuery,
      sortBy: this.sortBy,
      page: this.articlePage,
      pageSize: this.pageSize
    });
    this.articlePage = Math.min(this.articlePage, page.totalPages);
    this.renderArticleDirectory(lang, page, `#${this.tagDetail}`);
    document.title = `#${this.tagDetail} :: ${ui.brand}`;
    this.updateSeo(lang, `#${this.tagDetail}`, lang === "ru" ? `Материалы с тэгом #${this.tagDetail} в autophany.space.` : `Articles tagged #${this.tagDetail} in autophany.space.`);
    this.updateRightProcess(lang, { tag: this.tagDetail, matches: page.totalItems });
    setView(VIEW_LIST);
  }

  private renderNotFound(lang: Lang, slug?: string): void {
    this.activeArticle = null;
    this.activeInfoFile = null;
    this.activePanel = PANEL_HOME;
    this.tagDetail = null;
    this.exitZenMode();
    document.body.classList.add("not-found-mode");
    this.applyPanelState(lang);
    dom.treeHome.classList.remove("is-active");
    dom.treeArticles.classList.remove("is-active");
    dom.treeTags.classList.remove("is-active");
    dom.welcomeCommand.textContent = "$ dmesg | tail -2";
    dom.welcomeTitle.textContent = "signal lost";
    dom.welcomeLead.textContent = "cd /";
    dom.welcomeBody.textContent = "";
    const path = slug || window.location.pathname;
    dom.errorTitle.textContent = "signal lost";
    dom.errorText.innerHTML = '<a class="error-root-link" href="/" data-internal="true" aria-label="cd /">cd /</a>';
    dom.renderIndicator.textContent = '$ dmesg | grep ENOENT';
    document.title = "signal lost :: " + text(lang).brand;
    this.updateSeo(lang, "signal lost", lang === "ru" ? "Маршрут потерян." : "Route signal lost.", false);
    dom.processLog.innerHTML = [
      '<span class="shell-prompt">guest@cray-1:~$</span> <span class="shell-cmd">dmesg | tail -4</span>',
      '<span class="meta-rule" aria-hidden="true"></span>',
      '<span class="meta-key">errno</span>: ENOENT',
      '<span class="meta-key">route</span>: ' + this.escapeHtml(path),
      '<span class="meta-key">signal</span>: lost',
      '<span class="meta-key">recovery</span>: <a class="meta-tag-link" href="/" data-internal="true">cd /</a>'
    ].join("<br>");
    setView(VIEW_ERROR);
  }

  private escapeHtml(value: string): string {
    return value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  private escapeShell(value: string): string {
    return value.replace(/["\\$]/g, "\\$&");
  }

  private renderArticleDirectory(lang: Lang, page: PageModel<ArticleMeta>, title: string): void {
    renderArticleList(lang, page.items, text(lang).views, this.getReads);
    dom.listTitle.textContent = title;
    dom.tagsSubtitle.textContent = "";
    this.setPagerState(controls.articles, this.articlePage, page.totalPages);
  }

  private applyPanelState(lang: Lang): void {
    const showArticleList = this.activePanel === PANEL_ARTICLES || this.tagDetail !== null;
    dom.homeFilesPanel.classList.toggle("hidden", this.activePanel !== PANEL_HOME);
    dom.articlesPanel.classList.toggle("hidden", !showArticleList);
    dom.tagsPanel.classList.toggle("hidden", this.activePanel !== PANEL_TAGS || this.tagDetail !== null);
    dom.articleView.classList.add("hidden");
    dom.errorView.classList.add("hidden");
    dom.treeHome.classList.toggle("is-active", this.activePanel === PANEL_HOME);
    dom.treeArticles.classList.toggle("is-active", this.activePanel === PANEL_ARTICLES);
    dom.treeTags.classList.toggle("is-active", this.activePanel === PANEL_TAGS);
    dom.pwdLine.textContent = sidebarCommand();
    dom.renderIndicator.textContent = this.currentHeaderCommand();
    this.setPagerState(controls.articles, 1, 1);
    dom.tagsHeadline.textContent = this.tagDetail ? `#${this.tagDetail}` : text(lang).tagsHeadline;
    this.updateLeftInfo(lang);

    if (this.activeArticle === null && this.activeInfoFile === null) {
      this.tocController.clear({ articleContent: dom.articleContent, tocPanel: dom.tocPanel, tocList: dom.tocList });
    }
  }

  private currentHeaderCommand(): string {
    const query = this.activePanel === PANEL_TAGS && !this.tagDetail ? this.tagSearchQuery : this.articleSearchQuery;
    return headerCommand(this.activePanel, this.tagDetail ?? undefined, {
      sortBy: this.activePanel === PANEL_TAGS && !this.tagDetail ? this.tagSortBy : this.sortBy,
      pageSize: this.activePanel === PANEL_TAGS && !this.tagDetail ? this.tagPageSize : this.pageSize,
      query: query || undefined,
      maxColumns: this.commandColumns()
    });
  }

  private commandColumns(): number {
    const rectWidth = dom.renderIndicator.getBoundingClientRect().width;
    const parentWidth = dom.renderIndicator.parentElement?.getBoundingClientRect().width ?? 0;
    const width = Math.max(0, Math.min(rectWidth || parentWidth || 760, parentWidth || rectWidth || 760));
    const approxCharWidth = 10.8;
    return Math.max(28, Math.min(54, Math.floor((width - 28) / approxCharWidth)));
  }

  private enterZenMode(): void {
    if (!this.activeArticle) return;
    document.body.classList.add("zen-mode");
    dom.articleContent.tabIndex = -1;
    dom.articleContent.focus({ preventScroll: true });
  }

  private exitZenMode(): void {
    document.body.classList.remove("zen-mode", "zen-top-hover");
    this.zenTopHover = false;
  }

  private updateLeftInfo(lang: Lang): void {
    if (this.activeArticle) {
      this.applyWelcomeText(this.activeArticle.title[lang], this.activeArticle.description[lang]);
      dom.welcomeCommand.textContent = `$ sed -n '1,2p' ${this.metaFileName(this.activeArticle.slug, "tex")}`;
      return;
    }

    if (this.activeInfoFile) {
      this.applyWelcomeText(this.activeInfoFile.title[lang], this.activeInfoFile.description[lang]);
      dom.welcomeCommand.textContent = `$ sed -n '1,2p' ${this.activeInfoFile.slug}.meta`;
      return;
    }

    const info = panelInfo(lang, this.activePanel, this.tagDetail ?? undefined);
    dom.welcomeCommand.textContent = this.leftInfoCommand();
    this.applyWelcomeText(info.title, info.lead, info.body);
  }

  private applyWelcomeText(title: string, lead: string, body = ""): void {
    dom.welcomeTitle.textContent = title;
    dom.welcomeLead.textContent = lead;
    dom.welcomeBody.textContent = body;
  }

  private leftInfoCommand(): string {
    if (this.activePanel === PANEL_TAGS && this.tagDetail) return `$ sed -n '1,2p' ${this.metaFileName(this.tagDetail, "tex")}`;
    return "$ sed -n '1,2p' .meta";
  }

  private metaFileName(slug: string, extension: string): string {
    return `${slug}.${extension}.meta`;
  }

  private async renderInfoFile(lang: Lang, slug: string, renderId: number): Promise<void> {
    const file = findInfoFile(slug);
    if (!file) {
      this.renderNotFound(lang, slug);
      return;
    }

    const html = await renderInfoFileHtml(file, lang);
    if (renderId !== this.routeRenderId) return;

    this.setRootContext();
    this.activeInfoFile = file;
    this.applyPanelState(lang);
    renderArticleContent(html);
    this.renderArticleToc();
    this.setArticleActionsVisible(false);
    this.applyWelcomeText(file.title[lang], file.description[lang]);
    dom.renderIndicator.textContent = infoFileOpenCommand(file.slug);
    document.title = file.title[lang] + " :: " + text(lang).brand;
    this.updateSeo(lang, file.title[lang], file.description[lang]);
    this.updateRightProcess(lang, { infoFile: file });
    setView(VIEW_ARTICLE);
  }

  private async renderArticle(lang: Lang, slug: string, renderId: number): Promise<void> {
    const article = this.articles.find((item) => item.slug === slug);
    if (!article || !hasTranslation(article, lang)) {
      this.renderNotFound(lang, slug);
      return;
    }

    const html = await loadArticleContent(slug, lang);
    if (renderId !== this.routeRenderId) return;
    if (!html) {
      this.renderNotFound(lang, slug);
      return;
    }

    this.setArticlesContext();
    this.activeArticle = article;
    this.applyPanelState(lang);
    this.incrementReadsForRoute(lang, slug);
    renderArticleContent(html);
    this.removeDuplicateArticleHeading(article.title[lang]);
    this.appendArticleLinks(lang, article);
    this.cacheCurrentArticleStats(lang, slug);
    this.renderArticleToc();
    this.setArticleActionsVisible(true);
    dom.downloadPdfBtn.textContent = "pdf";
    dom.editArticleBtn.textContent = "edit";
    dom.zenModeBtn.textContent = "zen";
    this.applyWelcomeText(article.title[lang], article.description[lang]);
    dom.renderIndicator.textContent = articleOpenCommand(article.slug);
    document.title = `${article.title[lang]} :: ${text(lang).brand}`;
    this.updateSeo(lang, article.title[lang], article.description[lang]);
    this.updateRightProcess(lang, { article });
    setView(VIEW_ARTICLE);
  }

  private removeDuplicateArticleHeading(title: string): void {
    const firstHeading = dom.articleContent.querySelector<HTMLElement>("h1:first-child, h2:first-child");
    if (!firstHeading) return;
    const headingText = this.normalizeHeadingText(firstHeading.textContent ?? "");
    const titleText = this.normalizeHeadingText(title);
    if (headingText === titleText) firstHeading.remove();
  }

  private normalizeHeadingText(value: string): string {
    return value.replace(/#$/, "").replace(/\s+/g, " ").trim().toLowerCase();
  }

  private appendArticleLinks(lang: Lang, article: ArticleMeta): void {
    const sorted = [...this.articlesForLang(lang)].sort((a, b) => b.date.localeCompare(a.date));
    const currentIndex = sorted.findIndex((item) => item.slug === article.slug);
    const previous = currentIndex > 0 ? sorted[currentIndex - 1] : null;
    const next = currentIndex >= 0 && currentIndex < sorted.length - 1 ? sorted[currentIndex + 1] : null;

    const topNav = document.createElement("nav");
    topNav.className = "article-breadcrumbs";
    topNav.setAttribute("aria-label", "Breadcrumbs");
    const current = document.createElement("span");
    current.textContent = article.slug;
    topNav.append(this.makeInlineLink(homePath(lang), "root"), document.createTextNode(" / "), this.makeInlineLink(articlesPath(lang), "articles"), document.createTextNode(" / "), current);

    const bottomNav = document.createElement("nav");
    bottomNav.className = "article-seo-links";
    bottomNav.setAttribute("aria-label", "Article links");
    const tags = document.createElement("p");
    tags.className = "article-tag-links";
    tags.append(document.createTextNode("tags: "));
    for (const tag of article.tags) tags.append(this.makeInlineLink(tagPath(lang, tag), `#${tag}`), document.createTextNode(" "));
    const files = document.createElement("p");
    files.className = "article-file-links";
    files.append(this.makeInlineLink(articlePdfPath(lang, article.slug), "download PDF", { newTab: true }));
    const neighbors = document.createElement("p");
    neighbors.className = "article-neighbor-links";
    if (previous) neighbors.append(this.makeInlineLink(articlePath(lang, previous.slug), `previous: ${previous.title[lang]}`));
    if (previous && next) neighbors.append(document.createTextNode(" · "));
    if (next) neighbors.append(this.makeInlineLink(articlePath(lang, next.slug), `next: ${next.title[lang]}`));
    bottomNav.append(tags, files);
    if (previous || next) bottomNav.append(neighbors);
    dom.articleContent.prepend(topNav);
    dom.articleContent.append(bottomNav);
  }

  private makeInlineLink(href: string, label: string, options: { newTab?: boolean } = {}): HTMLAnchorElement {
    const link = document.createElement("a");
    link.href = href;
    link.textContent = label;
    if (options.newTab) {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    } else {
      link.dataset.internal = "true";
    }
    return link;
  }

  private renderArticleToc(): void {
    const hashId = this.tocController.render({ articleContent: dom.articleContent, tocPanel: dom.tocPanel, tocList: dom.tocList });
    cancelAnimationFrame(this.tocScrollFrame);
    if (hashId) {
      this.tocScrollFrame = requestAnimationFrame(() => {
        this.openHeadingAnchor(hashId, false);
      });
    }
  }

  private openHeadingAnchor(id: string, pushState: boolean): void {
    const target = document.getElementById(id);
    if (!target) return;
    const url = `${window.location.pathname}${window.location.search}#${encodeURIComponent(id)}`;
    if (pushState && url !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.replaceState({}, "", url);
    }
    this.tocController.markActive(dom.tocList, id);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const headerOffset = this.headerOffset();
    const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY - headerOffset);
    window.scrollTo({ top, behavior: reducedMotion ? "auto" : "smooth" });
  }

  private headerOffset(): number {
    const raw = getComputedStyle(document.documentElement).getPropertyValue("--header-height-offset").trim();
    const value = Number.parseFloat(raw);
    return Number.isFinite(value) ? value * (raw.endsWith("rem") ? this.rootFontSize() : 1) : 108;
  }

  private rootFontSize(): number {
    return Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
  }

  private articlesForLang(lang: Lang): ArticleMeta[] {
    const cached = this.articlesByLang.get(lang);
    if (cached) return cached;
    const articles = this.articles.filter((article) => hasTranslation(article, lang));
    this.articlesByLang.set(lang, articles);
    return articles;
  }


  private tagsForLang(lang: Lang): TagInfo[] {
    const cached = this.tagCountsByLang.get(lang);
    if (cached) return cached;
    const counts = countTags(this.articlesForLang(lang));
    this.tagCountsByLang.set(lang, counts);
    return counts;
  }

  private renderTagPager(page: TagPageModel): void {
    this.setPagerState(controls.tags, this.tagPage, page.totalPages);
  }

  private setPagerState(group: (typeof controls)["articles"] | (typeof controls)["tags"], page: number, totalPages: number): void {
    group.pageInfo.textContent = `${page}/${totalPages}`;
    group.pagePrev.disabled = page <= 1;
    group.pageNext.disabled = page >= totalPages;
  }

  private getReads = (slug: string): number => {
    const raw = localGet(`reads:${slug}`);
    return raw ? Number.parseInt(raw, 10) || 0 : 0;
  };

  private incrementReads(slug: string): void {
    localSet(`reads:${slug}`, String(this.getReads(slug) + 1));
  }

  private incrementReadsForRoute(lang: Lang, slug: string): void {
    const key = `${lang}:${slug}`;
    if (this.currentArticleReadKey === key) return;
    this.currentArticleReadKey = key;
    this.incrementReads(slug);
  }

  private updateRightProcess(lang: Lang, context?: RenderContext): void {
    dom.processLog.innerHTML = processSnapshotHtml({
      lang,
      panel: this.activePanel,
      tag: context?.tag ?? this.tagDetail ?? undefined,
      query: this.activePanel === "tags" && !this.tagDetail ? this.tagSearchQuery || undefined : this.articleSearchQuery || undefined,
      article: context?.article ?? this.activeArticle ?? undefined,
      infoFile: context?.infoFile ?? this.activeInfoFile ?? undefined,
      reads: context?.article ? this.getReads(context.article.slug) : this.activeArticle ? this.getReads(this.activeArticle.slug) : undefined,
      matches: context?.matches,
      ...this.currentTextStats()
    });
  }

  private currentTextStats(): { words: number; chars: number } {
    if (!this.activeArticle) return { words: 0, chars: 0 };
    return this.articleStats.get(this.articleStatsKey(parseRoute().lang, this.activeArticle.slug)) ?? { words: 0, chars: 0 };
  }

  private cacheCurrentArticleStats(lang: Lang, slug: string): void {
    const key = this.articleStatsKey(lang, slug);
    if (this.articleStats.has(key)) this.articleStats.delete(key);
    this.articleStats.set(key, countTextStats(dom.articleContent.textContent ?? ""));
    while (this.articleStats.size > MAX_ARTICLE_STATS_CACHE) {
      const oldestKey = this.articleStats.keys().next().value as string | undefined;
      if (!oldestKey) break;
      this.articleStats.delete(oldestKey);
    }
  }

  private articleStatsKey(lang: Lang, slug: string): string {
    return `${lang}:${slug}`;
  }

  private updateSeo(lang: Lang, title: string, description: string, indexable = true): void {
    const route = parseRoute();
    const canonicalPath = this.canonicalPathForRoute(lang, route);
    updateSeoMeta({
      lang,
      title,
      description,
      indexable,
      type: this.activeArticle ? PAGE_ARTICLE : "website",
      canonicalPath,
      alternatePaths: indexable ? this.alternatePathsForRoute(route) : undefined,
      structuredData: indexable ? this.structuredDataForRoute(lang, title, description, canonicalPath) : undefined
    });
  }

  private canonicalPathForRoute(lang: Lang, route: Route): string {
    if (this.activeArticle) return articlePath(lang, this.activeArticle.slug);
    if (this.activeInfoFile) return infoFilePath(lang, this.activeInfoFile.slug);
    if (route.page === PAGE_ARTICLES) return articlesPath(lang);
    if (route.page === PAGE_TAGS && route.tag) return tagPath(lang, route.tag);
    if (route.page === PAGE_TAGS) return tagsPath(lang);
    if (route.page === PAGE_INFO_FILE) return infoFilePath(lang, route.slug);
    return homePath(lang);
  }

  private alternatePathsForRoute(route: Route): Partial<Record<Lang | typeof DEFAULT_HREFLANG, string>> {
    if (this.activeArticle) {
      const paths: Partial<Record<Lang | typeof DEFAULT_HREFLANG, string>> = {};
      for (const lang of this.activeArticle.languages) paths[lang] = articlePath(lang, this.activeArticle.slug);
      paths[DEFAULT_HREFLANG] = paths[LANG_EN] ?? paths[LANG_RU];
      return paths;
    }
    if (route.page === PAGE_ARTICLES) return { [LANG_EN]: articlesPath(LANG_EN), [LANG_RU]: articlesPath(LANG_RU), [DEFAULT_HREFLANG]: articlesPath(LANG_EN) };
    if (route.page === PAGE_TAGS && route.tag) return { [LANG_EN]: tagPath(LANG_EN, route.tag), [LANG_RU]: tagPath(LANG_RU, route.tag), [DEFAULT_HREFLANG]: tagPath(LANG_EN, route.tag) };
    if (route.page === PAGE_TAGS) return { [LANG_EN]: tagsPath(LANG_EN), [LANG_RU]: tagsPath(LANG_RU), [DEFAULT_HREFLANG]: tagsPath(LANG_EN) };
    if (route.page === PAGE_INFO_FILE) return { [LANG_EN]: infoFilePath(LANG_EN, route.slug), [LANG_RU]: infoFilePath(LANG_RU, route.slug), [DEFAULT_HREFLANG]: infoFilePath(LANG_EN, route.slug) };
    return { [LANG_EN]: homePath(LANG_EN), [LANG_RU]: homePath(LANG_RU), [DEFAULT_HREFLANG]: homePath(LANG_EN) };
  }

  private structuredDataForRoute(lang: Lang, title: string, description: string, canonicalPath: string): unknown[] {
    const url = window.location.origin + canonicalPath;
    if (this.activeArticle) {
      return [
        {
          "@context": "https://schema.org",
          "@type": "BlogPosting",
          headline: this.activeArticle.title[lang],
          description: this.activeArticle.description[lang],
          author: { "@type": "Person", name: "autophany.space" },
          datePublished: this.activeArticle.date,
          dateModified: this.activeArticle.date,
          mainEntityOfPage: { "@type": "WebPage", "@id": url },
          inLanguage: lang,
          url,
          keywords: this.activeArticle.tags.join(", "),
          isPartOf: { "@type": "Blog", name: "autophany.space", url: window.location.origin + homePath(lang) }
        },
        this.breadcrumbStructuredData([[text(lang).brand, homePath(lang)], [text(lang).listTitle, articlesPath(lang)], [this.activeArticle.title[lang], articlePath(lang, this.activeArticle.slug)]])
      ];
    }
    return [{ "@context": "https://schema.org", "@type": "WebSite", name: "autophany.space", description, inLanguage: lang, url }, this.breadcrumbStructuredData([[title, canonicalPath]])];
  }

  private breadcrumbStructuredData(items: Array<[string, string]>): unknown {
    return {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: items.map(([name, path], index) => ({ "@type": "ListItem", position: index + 1, name, item: window.location.origin + path }))
    };
  }

  private openCurrentArticleEditor(): void {
    if (!this.activeArticle) return;
    const route = parseRoute();
    const url = `${GITHUB_EDIT_BASE}/${encodeURIComponent(this.activeArticle.slug)}.${route.lang}.tex`;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  private openCurrentArticlePdf(): void {
    if (!this.activeArticle) return;
    const route = parseRoute();
    if (route.page !== PAGE_ARTICLE) return;
    const pdfUrl = articlePdfPath(route.lang, this.activeArticle.slug);
    window.open(pdfUrl, "_blank", "noopener,noreferrer");
  }

  private async renderRoute(options: { resetScroll: boolean }): Promise<void> {
    const renderId = ++this.routeRenderId;
    const route = parseRoute();

    try {
      document.body.classList.remove("not-found-mode");
      if (route.page !== PAGE_ARTICLE) {
        this.exitZenMode();
        this.currentArticleReadKey = null;
      }
      this.syncRouteState(route);
      this.applyStaticUi(route.lang);

      if (this.routeNeedsArticleIndex(route)) await this.ensureArticlesLoaded();
      if (renderId !== this.routeRenderId) return;

      switch (route.page) {
        case PAGE_NOT_FOUND:
          this.renderNotFound(route.lang, route.slug);
          break;
        case PAGE_ARTICLE:
          await this.renderArticle(route.lang, route.slug, renderId);
          break;
        case PAGE_INFO_FILE:
          await this.renderInfoFile(route.lang, route.slug, renderId);
          break;
        default:
          this.renderHome(route.lang);
      }
      if (renderId === this.routeRenderId && options.resetScroll) window.scrollTo({ top: 0, behavior: "auto" });
    } catch {
      if (renderId === this.routeRenderId) setView(VIEW_ERROR);
    }
  }

  private routeNeedsArticleIndex(route: Route): boolean {
    return route.page === PAGE_ARTICLES || route.page === PAGE_TAGS || route.page === PAGE_ARTICLE;
  }

  private async ensureArticlesLoaded(): Promise<void> {
    if (this.articlesLoaded) return;
    this.articles = await loadArticleIndex();
    this.tagCountsByLang.clear();
    this.articlesByLang.clear();
    this.articleStats.clear();
    this.articlesLoaded = true;
  }

  private syncRouteState(route: Route): void {
    this.activeArticle = null;
    this.activeInfoFile = null;

    if (route.page !== PAGE_ARTICLE) sessionRemove("article-back-path");

    switch (route.page) {
      case PAGE_NOT_FOUND:
      case PAGE_INFO_FILE:
        this.setRootContext();
        break;
      case PANEL_HOME:
        this.activePanel = route.panel;
        this.tagDetail = null;
        this.activeTag = ALL_TAGS;
        break;
      case PAGE_ARTICLES:
        this.setArticlesContext();
        this.articlePage = this.pageFromUrl();
        break;
      case PAGE_TAGS: {
        this.activePanel = PANEL_TAGS;
        this.tagDetail = route.tag ?? null;
        this.activeTag = this.tagDetail ?? ALL_TAGS;
        if (this.tagDetail) this.articlePage = this.pageFromUrl();
        else this.tagPage = this.pageFromUrl();
        break;
      }
      default:
        this.setArticlesContext();
    }
  }

  private setRootContext(): void {
    this.activePanel = PANEL_HOME;
    this.tagDetail = null;
    this.activeTag = ALL_TAGS;
  }

  private setArticlesContext(): void {
    this.activePanel = PANEL_ARTICLES;
    this.tagDetail = null;
    this.activeTag = ALL_TAGS;
  }

  private setArticleActionsVisible(isVisible: boolean): void {
    dom.downloadPdfBtn.classList.toggle("hidden", !isVisible);
    dom.zenModeBtn.classList.toggle("hidden", !isVisible);
    dom.editArticleBtn.classList.toggle("hidden", !isVisible);
  }

  private applyStaticUi(lang: Lang): void {
    applyUiText(lang);
    dom.langSwitcher.value = lang;
    controls.articles.sortSelect.value = this.sortBy;
    this.pageSize = this.normalizePageSize(this.pageSize);
    this.tagPageSize = this.normalizePageSize(this.tagPageSize);
    controls.articles.sizeSelect.value = String(this.pageSize);
    controls.tags.sortSelect.value = this.tagSortBy;
    controls.tags.sizeSelect.value = String(this.tagPageSize);
    controls.articles.searchInput.value = this.articleSearchQuery;
    controls.tags.searchInput.value = this.tagSearchQuery;
    dom.brandLink.href = "/";
    dom.treeHome.href = "/";
    dom.treeArticles.href = articlesPath(lang);
    dom.treeTags.href = tagsPath(lang);
    dom.backLink.href = this.backHref(lang);
  }

  private backHref(lang: Lang): string {
    const route = parseRoute();
    if (route.page === PAGE_INFO_FILE) return homePath(lang);
    const stored = sessionGet("article-back-path");
    if (stored && new RegExp(`^/${lang}/(articles|tags)(/|$)?`).test(stored)) return stored;
    return articlesPath(lang);
  }

  private pageFromUrl(): number {
    const raw = new URLSearchParams(window.location.search).get("page");
    const value = raw ? Number.parseInt(raw, 10) : 1;
    return Number.isFinite(value) && value > 0 ? value : 1;
  }

  private setPageParam(page: number, replace = false): void {
    const route = parseRoute();
    if (route.page !== PAGE_ARTICLES && route.page !== PAGE_TAGS) return;
    const url = new URL(window.location.href);
    if (page <= 1) url.searchParams.delete("page");
    else url.searchParams.set("page", String(page));
    const next = `${url.pathname}${url.search}${url.hash}`;
    if (next === `${window.location.pathname}${window.location.search}${window.location.hash}`) return;
    if (replace) window.history.replaceState({}, "", next);
    else window.history.pushState({}, "", next);
  }

  private withPage(path: string, page: number): string {
    return page > 1 ? `${path}?page=${page}` : path;
  }

  private currentListPath(lang: Lang): string {
    if (this.activePanel === PANEL_TAGS) {
      const base = this.tagDetail ? tagPath(lang, this.tagDetail) : tagsPath(lang);
      return this.withPage(base, this.tagDetail ? this.articlePage : this.tagPage);
    }
    if (this.activePanel === PANEL_ARTICLES) return this.withPage(articlesPath(lang), this.articlePage);
    return articlesPath(lang);
  }
}

const app = new BlogApp();
void app.init();
