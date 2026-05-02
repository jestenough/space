import { ALL_TAGS, DEFAULT_PAGE_SIZE, GITHUB_EDIT_BASE, PAGE_SIZE_OPTIONS } from "../core/config";
import { articleDescription, articleTitle, hasTranslation, loadArticleIndex } from "../services/articleService";
import { panelInfo } from "../components/panels";
import { controls } from "../components/controls";
import { countTags } from "../components/directory";
import { TocController } from "../components/toc";
import { headerCommand, processSnapshotHtml, sidebarCommand } from "../components/shell";
import { dom } from "../ui/dom";
import { applyUiText, label, text } from "../ui/i18n";
import { parseRoute, toLang } from "../router/router";
import { articlePath, articlesPath, homePath, infoFilePath, tagPath, tagsPath } from "../router/routePaths";
import { pdfService } from "../services/pdfService";
import { zenModeController } from "../features/zen/zenModeController";
import { seoService } from "../services/seoService";
import { storageService } from "../services/storageService";
import { DebounceDelay, StorageKey, SessionKey } from "../core/enums";
import { countTextStats } from "../features/articles/textStats";
import { themeService, THEMES } from "../services/themeService";
import { DEFAULT_LANG, languagesFromArticles } from "../core/languages";
import type { ArticleMeta, InfoFileMeta, Lang, Route, TagInfo, Theme } from "../core/types";
import { setView } from "../ui/view";
import { notFoundView } from "../ui/views/notFoundView";
import { ArticlePageController } from "../features/articles/articlePageController";
import { ArticleListController } from "../features/articles/articleListController";
import { TagPageController } from "../features/tags/tagPageController";
import { InfoFileController } from "../features/info/infoFileController";
import { HomeController } from "../features/home/homeController";
import { AppEventController } from "./appEventController";
import { AppState } from "./appState";
import { RouteController } from "./routeController";

type RenderContext = { article?: ArticleMeta; infoFile?: InfoFileMeta; tag?: string; matches?: number };
const MAX_ARTICLE_STATS_CACHE = 80;

const PANEL_HOME = "home" as const;
const PANEL_ARTICLES = "articles" as const;
const PANEL_TAGS = "tags" as const;
const PAGE_ARTICLE = "article" as const;
const PAGE_ARTICLES = "articles" as const;
const PAGE_TAGS = "tags" as const;
const PAGE_INFO_FILE = "info-file" as const;
const PAGE_NOT_FOUND = "not-found" as const;
const VIEW_ERROR = "error" as const;

export class AppController {
  private readonly state = new AppState();
  private renderFrame = 0;
  private headerFrame = 0;
  private tocScrollFrame = 0;
  private searchRenderTimer: number | null = null;
  private tocController = new TocController();
  private readonly articlePageController: ArticlePageController;
  private readonly articleListController: ArticleListController;
  private readonly tagPageController: TagPageController;
  private readonly infoFileController: InfoFileController;
  private readonly homeController: HomeController;
  private readonly eventController = new AppEventController();
  private readonly routeController: RouteController;

  constructor() {
    this.articlePageController = new ArticlePageController({
      currentRenderId: () => this.state.routeRenderId,
      renderNotFound: (lang, slug) => this.renderNotFound(lang, slug),
      setArticlesContext: () => this.setArticlesContext(),
      setActiveArticle: (article) => { this.state.activeArticle = article; },
      applyPanelState: (lang) => this.applyPanelState(lang),
      renderArticleToc: () => this.renderArticleToc(),
      setArticleActionsVisible: (isVisible) => this.setArticleActionsVisible(isVisible),
      applyWelcomeText: (title, lead, body) => this.applyWelcomeText(title, lead, body),
      cacheCurrentArticleStats: (lang, slug) => this.cacheCurrentArticleStats(lang, slug),
      updateSeo: (lang, title, description, indexable) => this.updateSeo(lang, title, description, indexable),
      updateRightProcess: (lang, context) => this.updateRightProcess(lang, context)
    });
    this.infoFileController = new InfoFileController({
      currentRenderId: () => this.state.routeRenderId,
      renderNotFound: (lang, slug) => this.renderNotFound(lang, slug),
      setRootContext: () => this.setRootContext(),
      setActiveInfoFile: (file) => { this.state.activeInfoFile = file; },
      applyPanelState: (lang) => this.applyPanelState(lang),
      renderArticleToc: () => this.renderArticleToc(),
      setArticleActionsVisible: (isVisible) => this.setArticleActionsVisible(isVisible),
      applyWelcomeText: (title, lead, body) => this.applyWelcomeText(title, lead, body),
      updateSeo: (lang, title, description, indexable) => this.updateSeo(lang, title, description, indexable),
      updateRightProcess: (lang, context) => this.updateRightProcess(lang, context)
    });
    this.articleListController = new ArticleListController({
      articlesForLang: (lang) => this.articlesForLang(lang),
      getQuery: () => this.state.articleSearchQuery,
      getSortBy: () => this.state.sortBy,
      getPage: () => this.state.articlePage,
      setPage: (page) => { this.state.articlePage = page; },
      getPageSize: () => this.state.pageSize,
      applyPanelState: (lang) => this.applyPanelState(lang),
      updateSeo: (lang, title, description, indexable) => this.updateSeo(lang, title, description, indexable),
      updateRightProcess: (lang, context) => this.updateRightProcess(lang, context)
    });
    this.tagPageController = new TagPageController({
      articlesForLang: (lang) => this.articlesForLang(lang),
      tagsForLang: (lang) => this.tagsForLang(lang),
      getTagDetail: () => this.state.tagDetail,
      getActiveTag: () => this.state.activeTag,
      getArticleQuery: () => this.state.articleSearchQuery,
      getTagQuery: () => this.state.tagSearchQuery,
      getArticleSortBy: () => this.state.sortBy,
      getTagSortBy: () => this.state.tagSortBy,
      getArticlePage: () => this.state.articlePage,
      setArticlePage: (page) => { this.state.articlePage = page; },
      getTagPage: () => this.state.tagPage,
      setTagPage: (page) => { this.state.tagPage = page; },
      getArticlePageSize: () => this.state.pageSize,
      getTagPageSize: () => this.state.tagPageSize,
      applyPanelState: (lang) => this.applyPanelState(lang),
      renderNotFound: (lang, slug) => this.renderNotFound(lang, slug),
      updateSeo: (lang, title, description, indexable) => this.updateSeo(lang, title, description, indexable),
      updateRightProcess: (lang, context) => this.updateRightProcess(lang, context)
    });
    this.homeController = new HomeController({
      applyPanelState: (lang) => this.applyPanelState(lang),
      updateSeo: (lang, title, description, indexable) => this.updateSeo(lang, title, description, indexable),
      updateRightProcess: (lang) => this.updateRightProcess(lang)
    });
    this.routeController = new RouteController({
      nextRenderId: () => ++this.state.routeRenderId,
      currentRenderId: () => this.state.routeRenderId,
      exitZenMode: () => this.exitZenMode(),
      syncRouteState: (route) => this.syncRouteState(route),
      applyStaticUi: (lang) => this.applyStaticUi(lang),
      ensureArticlesLoaded: () => this.ensureArticlesLoaded(),
      renderNotFound: (lang, slug) => this.renderNotFound(lang, slug),
      renderArticle: (lang, slug, renderId) => this.articlePageController.render(lang, slug, renderId),
      renderInfoFile: (lang, slug, renderId) => this.infoFileController.render(lang, slug, renderId),
      renderIndexRoute: (lang) => this.renderIndexRoute(lang),
      setErrorView: () => setView(VIEW_ERROR)
    });
  }

  async init(): Promise<void> {
    themeService.initBeforeRender();
    this.syncTheme(storageService.get(StorageKey.Theme));
    this.eventController.bind({
      getActivePanel: () => this.state.activePanel,
      getTagDetail: () => this.state.tagDetail,
      getArticlePage: () => this.state.articlePage,
      setArticlePage: (page) => { this.state.articlePage = page; },
      getTagPage: () => this.state.tagPage,
      setTagPage: (page) => { this.state.tagPage = page; },
      getArticleQuery: () => this.state.articleSearchQuery,
      setArticleQuery: (query) => { this.state.articleSearchQuery = query; },
      getTagQuery: () => this.state.tagSearchQuery,
      setTagQuery: (query) => { this.state.tagSearchQuery = query; },
      setSortBy: (sortBy) => { this.state.sortBy = sortBy; },
      setPageSize: (pageSize) => { this.state.pageSize = pageSize; },
      setTagSortBy: (sortBy) => { this.state.tagSortBy = sortBy; },
      setTagPageSize: (pageSize) => { this.state.tagPageSize = pageSize; },
      currentListPath: (lang) => this.currentListPath(lang),
      navigateTo: (path) => this.navigateTo(path),
      renderRoute: (options) => this.renderRoute(options),
      scheduleRender: () => this.scheduleRender(),
      scheduleSearchRender: () => this.scheduleSearchRender(),
      scheduleHeaderUpdate: () => this.scheduleHeaderUpdate(),
      setPageParam: (page, replace) => this.setPageParam(page, replace),
      cycleTheme: () => this.cycleTheme(),
      syncTheme: (value) => this.syncTheme(value),
      enterZenMode: () => this.enterZenMode(),
      exitZenMode: () => this.exitZenMode(),
      openCurrentArticlePdf: () => this.openCurrentArticlePdf(),
      openCurrentArticleEditor: () => this.openCurrentArticleEditor(),
      openHeadingAnchor: (id, pushState) => this.openHeadingAnchor(id, pushState),
      changeLanguage: () => this.changeLanguage()
    });
    await this.renderRoute({ resetScroll: false });
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
    }, DebounceDelay.Search);
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
    if (route.page === PAGE_ARTICLE && this.state.activeArticle && hasTranslation(this.state.activeArticle, targetLang)) {
      this.navigateTo(articlePath(targetLang, this.state.activeArticle.slug));
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
    const current = dom.themeSwitcher.value as Theme;
    const idx = Math.max(0, THEMES.indexOf(current));
    const next = THEMES[(idx + 1) % THEMES.length];
    this.syncTheme(next);
  }

  private syncTheme(value: string | null): void {
    const theme = themeService.apply(value);
    storageService.set(StorageKey.Theme, theme);
    dom.themeSwitcher.value = theme;
    dom.themeLabel.textContent = `${text(parseRoute().lang).theme}${theme}`;
  }

  private normalizePageSize(value: number): number {
    return PAGE_SIZE_OPTIONS.includes(value as (typeof PAGE_SIZE_OPTIONS)[number]) ? value : DEFAULT_PAGE_SIZE;
  }

  private renderIndexRoute(lang: Lang): void {
    if (this.state.activePanel === PANEL_HOME) {
      this.homeController.render(lang);
      return;
    }
    if (this.state.activePanel === PANEL_ARTICLES) {
      this.articleListController.render(lang);
      return;
    }
    if (this.state.tagDetail) this.tagPageController.renderDetail(lang);
    else this.tagPageController.renderIndex(lang);
  }

  private renderNotFound(lang: Lang, slug?: string): void {
    this.state.activeArticle = null;
    this.state.activeInfoFile = null;
    this.state.activePanel = PANEL_HOME;
    this.state.tagDetail = null;
    this.exitZenMode();
    this.applyPanelState(lang);
    const path = slug || window.location.pathname;
    notFoundView.render(lang, path);
    this.updateSeo(lang, "signal lost", text(lang).routeLostDescription, false);
  }

  private applyPanelState(lang: Lang): void {
    const showArticleList = this.state.activePanel === PANEL_ARTICLES || this.state.tagDetail !== null;
    dom.homeFilesPanel.classList.toggle("hidden", this.state.activePanel !== PANEL_HOME);
    dom.articlesPanel.classList.toggle("hidden", !showArticleList);
    dom.tagsPanel.classList.toggle("hidden", this.state.activePanel !== PANEL_TAGS || this.state.tagDetail !== null);
    dom.articleView.classList.add("hidden");
    dom.errorView.classList.add("hidden");
    dom.treeHome.classList.toggle("is-active", this.state.activePanel === PANEL_HOME);
    dom.treeArticles.classList.toggle("is-active", this.state.activePanel === PANEL_ARTICLES);
    dom.treeTags.classList.toggle("is-active", this.state.activePanel === PANEL_TAGS);
    dom.pwdLine.textContent = sidebarCommand();
    dom.renderIndicator.textContent = this.currentHeaderCommand();
    this.setPagerState(controls.articles, 1, 1);
    dom.tagsHeadline.textContent = this.state.tagDetail ? `#${this.state.tagDetail}` : text(lang).tagsHeadline;
    this.updateLeftInfo(lang);

    if (this.state.activeArticle === null && this.state.activeInfoFile === null) {
      this.tocController.clear({ articleContent: dom.articleContent, tocPanel: dom.tocPanel, tocList: dom.tocList });
    }
  }

  private currentHeaderCommand(): string {
    const query = this.state.activePanel === PANEL_TAGS && !this.state.tagDetail ? this.state.tagSearchQuery : this.state.articleSearchQuery;
    return headerCommand(this.state.activePanel, this.state.tagDetail ?? undefined, {
      sortBy: this.state.activePanel === PANEL_TAGS && !this.state.tagDetail ? this.state.tagSortBy : this.state.sortBy,
      pageSize: this.state.activePanel === PANEL_TAGS && !this.state.tagDetail ? this.state.tagPageSize : this.state.pageSize,
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
    if (!this.state.activeArticle) return;
    zenModeController.enter(dom.articleContent, Boolean(this.state.activeArticle));
  }

  private exitZenMode(): void {
    zenModeController.exit();
  }

  private updateLeftInfo(lang: Lang): void {
    if (this.state.activeArticle) {
      this.applyWelcomeText(articleTitle(this.state.activeArticle, lang), articleDescription(this.state.activeArticle, lang));
      dom.welcomeCommand.textContent = `$ sed -n '1,2p' ${this.metaFileName(this.state.activeArticle.slug, "tex")}`;
      return;
    }

    if (this.state.activeInfoFile) {
      this.applyWelcomeText(label(this.state.activeInfoFile.title, lang), label(this.state.activeInfoFile.description, lang));
      dom.welcomeCommand.textContent = `$ sed -n '1,2p' ${this.state.activeInfoFile.slug}.meta`;
      return;
    }

    const info = panelInfo(lang, this.state.activePanel, this.state.tagDetail ?? undefined);
    dom.welcomeCommand.textContent = this.leftInfoCommand();
    this.applyWelcomeText(info.title, info.lead, info.body);
  }

  private applyWelcomeText(title: string, lead: string, body = ""): void {
    dom.welcomeTitle.textContent = title;
    dom.welcomeLead.textContent = lead;
    dom.welcomeBody.textContent = body;
  }

  private leftInfoCommand(): string {
    if (this.state.activePanel === PANEL_TAGS && this.state.tagDetail) return `$ sed -n '1,2p' ${this.metaFileName(this.state.tagDetail, "tex")}`;
    return "$ sed -n '1,2p' .meta";
  }

  private metaFileName(slug: string, extension: string): string {
    return `${slug}.${extension}.meta`;
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
    const cached = this.state.articlesByLang.get(lang);
    if (cached) return cached;
    const articles = this.state.articles.filter((article) => hasTranslation(article, lang));
    this.state.articlesByLang.set(lang, articles);
    return articles;
  }


  private tagsForLang(lang: Lang): TagInfo[] {
    const cached = this.state.tagCountsByLang.get(lang);
    if (cached) return cached;
    const counts = countTags(this.articlesForLang(lang));
    this.state.tagCountsByLang.set(lang, counts);
    return counts;
  }

  private setPagerState(group: (typeof controls)["articles"] | (typeof controls)["tags"], page: number, totalPages: number): void {
    group.pageInfo.textContent = `${page}/${totalPages}`;
    group.pagePrev.disabled = page <= 1;
    group.pageNext.disabled = page >= totalPages;
  }


  private updateRightProcess(lang: Lang, context?: RenderContext): void {
    dom.processLog.innerHTML = processSnapshotHtml({
      lang,
      panel: this.state.activePanel,
      tag: context?.tag ?? this.state.tagDetail ?? undefined,
      query: this.state.activePanel === "tags" && !this.state.tagDetail ? this.state.tagSearchQuery || undefined : this.state.articleSearchQuery || undefined,
      article: context?.article ?? this.state.activeArticle ?? undefined,
      infoFile: context?.infoFile ?? this.state.activeInfoFile ?? undefined,
      matches: context?.matches,
      ...this.currentTextStats()
    });
  }

  private currentTextStats(): { words: number; chars: number } {
    if (!this.state.activeArticle) return { words: 0, chars: 0 };
    return this.state.articleStats.get(this.articleStatsKey(parseRoute().lang, this.state.activeArticle.slug)) ?? { words: 0, chars: 0 };
  }

  private cacheCurrentArticleStats(lang: Lang, slug: string): void {
    const key = this.articleStatsKey(lang, slug);
    if (this.state.articleStats.has(key)) this.state.articleStats.delete(key);
    this.state.articleStats.set(key, countTextStats(dom.articleContent.textContent ?? ""));
    while (this.state.articleStats.size > MAX_ARTICLE_STATS_CACHE) {
      const oldestKey = this.state.articleStats.keys().next().value as string | undefined;
      if (!oldestKey) break;
      this.state.articleStats.delete(oldestKey);
    }
  }

  private articleStatsKey(lang: Lang, slug: string): string {
    return `${lang}:${slug}`;
  }


  private availableLanguages(): Lang[] {
    if (this.state.articlesLoaded) return languagesFromArticles(this.state.articles);
    const langs = Array.from(dom.langSwitcher.options, (option) => toLang(option.value));
    return langs.length ? [...new Set(langs)] : [DEFAULT_LANG];
  }

  private updateSeo(lang: Lang, title: string, description: string, indexable = true): void {
    seoService.updateRoute({
      lang,
      title,
      description,
      indexable,
      route: parseRoute(),
      activeArticle: this.state.activeArticle,
      activeInfoFile: this.state.activeInfoFile,
      availableLanguages: this.availableLanguages()
    });
  }

  private openCurrentArticleEditor(): void {
    if (!this.state.activeArticle) return;
    const route = parseRoute();
    const url = `${GITHUB_EDIT_BASE}/${encodeURIComponent(this.state.activeArticle.slug)}.${route.lang}.tex`;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  private openCurrentArticlePdf(): void {
    if (!this.state.activeArticle) return;
    const route = parseRoute();
    if (route.page !== PAGE_ARTICLE) return;
    pdfService.openArticlePdf(route.lang, this.state.activeArticle.slug);
  }

  private async renderRoute(options: { resetScroll: boolean }): Promise<void> {
    await this.routeController.render(options);
  }

  private async ensureArticlesLoaded(): Promise<void> {
    if (this.state.articlesLoaded) return;
    this.state.articles = await loadArticleIndex();
    this.state.tagCountsByLang.clear();
    this.state.articlesByLang.clear();
    this.state.articleStats.clear();
    this.state.articlesLoaded = true;
  }

  private syncRouteState(route: Route): void {
    this.state.activeArticle = null;
    this.state.activeInfoFile = null;

    if (route.page !== PAGE_ARTICLE) storageService.removeSession(SessionKey.ArticleBackPath);

    switch (route.page) {
      case PAGE_NOT_FOUND:
      case PAGE_INFO_FILE:
        this.setRootContext();
        break;
      case PANEL_HOME:
        this.state.activePanel = route.panel;
        this.state.tagDetail = null;
        this.state.activeTag = ALL_TAGS;
        break;
      case PAGE_ARTICLES:
        this.setArticlesContext();
        this.state.articlePage = this.pageFromUrl();
        break;
      case PAGE_TAGS: {
        this.state.activePanel = PANEL_TAGS;
        this.state.tagDetail = route.tag ?? null;
        this.state.activeTag = this.state.tagDetail ?? ALL_TAGS;
        if (this.state.tagDetail) this.state.articlePage = this.pageFromUrl();
        else this.state.tagPage = this.pageFromUrl();
        break;
      }
      default:
        this.setArticlesContext();
    }
  }

  private setRootContext(): void {
    this.state.activePanel = PANEL_HOME;
    this.state.tagDetail = null;
    this.state.activeTag = ALL_TAGS;
  }

  private setArticlesContext(): void {
    this.state.activePanel = PANEL_ARTICLES;
    this.state.tagDetail = null;
    this.state.activeTag = ALL_TAGS;
  }

  private setArticleActionsVisible(isVisible: boolean): void {
    dom.downloadPdfBtn.classList.toggle("hidden", !isVisible);
    dom.zenModeBtn.classList.toggle("hidden", !isVisible);
    dom.editArticleBtn.classList.toggle("hidden", !isVisible);
  }

  private applyStaticUi(lang: Lang): void {
    applyUiText(lang);
    this.syncTheme(dom.themeSwitcher.value);
    dom.langSwitcher.value = lang;
    controls.articles.sortSelect.value = this.state.sortBy;
    this.state.pageSize = this.normalizePageSize(this.state.pageSize);
    this.state.tagPageSize = this.normalizePageSize(this.state.tagPageSize);
    controls.articles.sizeSelect.value = String(this.state.pageSize);
    controls.tags.sortSelect.value = this.state.tagSortBy;
    controls.tags.sizeSelect.value = String(this.state.tagPageSize);
    controls.articles.searchInput.value = this.state.articleSearchQuery;
    controls.tags.searchInput.value = this.state.tagSearchQuery;
    dom.brandLink.href = "/";
    dom.treeHome.href = "/";
    dom.treeArticles.href = articlesPath(lang);
    dom.treeTags.href = tagsPath(lang);
    dom.backLink.href = this.backHref(lang);
  }

  private backHref(lang: Lang): string {
    const route = parseRoute();
    if (route.page === PAGE_INFO_FILE) return homePath(lang);
    const stored = storageService.getSession(SessionKey.ArticleBackPath);
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
    if (this.state.activePanel === PANEL_TAGS) {
      const base = this.state.tagDetail ? tagPath(lang, this.state.tagDetail) : tagsPath(lang);
      return this.withPage(base, this.state.tagDetail ? this.state.articlePage : this.state.tagPage);
    }
    if (this.state.activePanel === PANEL_ARTICLES) return this.withPage(articlesPath(lang), this.state.articlePage);
    return articlesPath(lang);
  }
}

