import { ROUTE_PREFIX, PAGE_SIZE_OPTIONS, DEFAULT_PAGE_SIZE } from "../core/config";
import { controls } from "../components/controls";
import { dom } from "../ui/dom";
import { keyboardController } from "../features/keyboard/keyboardController";
import { articleCopyController } from "../features/articles/articleCopyController";
import { zenModeController } from "../features/zen/zenModeController";
import { parseRoute } from "../router/router";
import { articlesPath, homePath, tagsPath } from "../router/routePaths";
import { storageService } from "../services/storageService";
import { SessionKey } from "../core/enums";
import { safeDecodeURIComponent } from "../core/url";
import type { SortBy, TagSortBy } from "../core/types";

export type AppEventControllerOptions = {
  getActivePanel: () => "home" | "articles" | "tags";
  getTagDetail: () => string | null;
  getArticlePage: () => number;
  setArticlePage: (page: number) => void;
  getTagPage: () => number;
  setTagPage: (page: number) => void;
  getArticleQuery: () => string;
  setArticleQuery: (query: string) => void;
  getTagQuery: () => string;
  setTagQuery: (query: string) => void;
  setSortBy: (sortBy: SortBy) => void;
  setPageSize: (pageSize: number) => void;
  setTagSortBy: (sortBy: TagSortBy) => void;
  setTagPageSize: (pageSize: number) => void;
  currentListPath: (lang: string) => string;
  navigateTo: (path: string) => void;
  renderRoute: (options: { resetScroll: boolean }) => Promise<void>;
  scheduleRender: () => void;
  scheduleSearchRender: () => void;
  scheduleHeaderUpdate: () => void;
  setPageParam: (page: number, replace?: boolean) => void;
  cycleTheme: () => void;
  syncTheme: (value: string | null) => void;
  enterZenMode: () => void;
  exitZenMode: () => void;
  openCurrentArticlePdf: () => void;
  openCurrentArticleEditor: () => void;
  openHeadingAnchor: (id: string, pushState: boolean) => void;
  changeLanguage: () => void;
};

const normalizePageSize = (value: number): number => PAGE_SIZE_OPTIONS.includes(value as (typeof PAGE_SIZE_OPTIONS)[number]) ? value : DEFAULT_PAGE_SIZE;
const normalizeQuery = (value: string): string => value.trim().toLowerCase();

const bindSearchInput = (input: HTMLInputElement, options: { get: () => string; set: (value: string) => void; onChange: () => void }): void => {
  input.addEventListener("input", () => {
    const next = normalizeQuery(input.value);
    if (next === options.get()) return;
    options.set(next);
    options.onChange();
  });
};

const bindSelectReset = (select: HTMLSelectElement, apply: () => void, afterChange: () => void): void => {
  select.addEventListener("change", () => {
    apply();
    afterChange();
  });
};

const bindPagerButton = (button: HTMLButtonElement, update: () => number, afterChange: (page: number) => void): void => {
  button.addEventListener("click", () => afterChange(update()));
};

export class AppEventController {
  bind(options: AppEventControllerOptions): void {
    document.addEventListener("click", (event) => this.handleDocumentClick(event, options));
    window.addEventListener("popstate", () => void options.renderRoute({ resetScroll: false }));
    window.addEventListener("resize", options.scheduleHeaderUpdate);

    keyboardController.bind({
      onArticles: () => options.navigateTo(articlesPath(parseRoute().lang)),
      onTags: () => options.navigateTo(tagsPath(parseRoute().lang)),
      onHome: () => options.navigateTo(homePath(parseRoute().lang)),
      onThemeCycle: options.cycleTheme,
      onSearchFocus: () => {
        if (options.getActivePanel() === "tags" && !options.getTagDetail()) controls.tags.searchInput.focus();
        else controls.articles.searchInput.focus();
      },
      onEscape: () => {
        options.exitZenMode();
        controls.articles.searchInput.blur();
        controls.tags.searchInput.blur();
      }
    });

    zenModeController.bindTopHover();
    articleCopyController.bind(dom.articleContent);
    dom.langSwitcher.addEventListener("change", options.changeLanguage);
    dom.themeSwitcher.addEventListener("change", () => options.syncTheme(dom.themeSwitcher.value));

    bindSearchInput(controls.articles.searchInput, {
      get: options.getArticleQuery,
      set: (value) => {
        options.setArticleQuery(value);
        options.setArticlePage(1);
      },
      onChange: () => {
        options.setPageParam(1, true);
        options.scheduleSearchRender();
      }
    });

    bindSearchInput(controls.tags.searchInput, {
      get: options.getTagQuery,
      set: (value) => {
        options.setTagQuery(value);
        options.setTagPage(1);
      },
      onChange: () => {
        options.setPageParam(1, true);
        options.scheduleSearchRender();
      }
    });

    bindSelectReset(controls.articles.sortSelect, () => {
      options.setSortBy(controls.articles.sortSelect.value as SortBy);
      options.setArticlePage(1);
    }, () => {
      options.setPageParam(1, true);
      options.scheduleRender();
    });

    bindSelectReset(controls.articles.sizeSelect, () => {
      options.setPageSize(normalizePageSize(Number.parseInt(controls.articles.sizeSelect.value, 10)));
      options.setArticlePage(1);
    }, () => {
      options.setPageParam(1, true);
      options.scheduleRender();
    });

    bindSelectReset(controls.tags.sortSelect, () => {
      options.setTagSortBy(controls.tags.sortSelect.value as TagSortBy);
      options.setTagPage(1);
    }, () => {
      options.setPageParam(1, true);
      options.scheduleRender();
    });

    bindSelectReset(controls.tags.sizeSelect, () => {
      options.setTagPageSize(normalizePageSize(Number.parseInt(controls.tags.sizeSelect.value, 10)));
      options.setTagPage(1);
    }, () => {
      options.setPageParam(1, true);
      options.scheduleRender();
    });

    bindPagerButton(controls.articles.pagePrev, () => Math.max(1, options.getArticlePage() - 1), (page) => {
      options.setArticlePage(page);
      options.setPageParam(page);
      void options.renderRoute({ resetScroll: false });
    });

    bindPagerButton(controls.articles.pageNext, () => options.getArticlePage() + 1, (page) => {
      options.setArticlePage(page);
      options.setPageParam(page);
      void options.renderRoute({ resetScroll: false });
    });

    bindPagerButton(controls.tags.pagePrev, () => Math.max(1, options.getTagPage() - 1), (page) => {
      options.setTagPage(page);
      options.setPageParam(page);
      void options.renderRoute({ resetScroll: false });
    });

    bindPagerButton(controls.tags.pageNext, () => options.getTagPage() + 1, (page) => {
      options.setTagPage(page);
      options.setPageParam(page);
      void options.renderRoute({ resetScroll: false });
    });

    dom.downloadPdfBtn.addEventListener("click", options.openCurrentArticlePdf);
    dom.editArticleBtn.addEventListener("click", options.openCurrentArticleEditor);
    dom.zenModeBtn.addEventListener("click", options.enterZenMode);
    dom.zenExitBtn.addEventListener("click", options.exitZenMode);
  }

  private handleDocumentClick(event: MouseEvent, options: AppEventControllerOptions): void {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const anchor = target.closest("a[href]") as HTMLAnchorElement | null;
    if (!anchor) {
      const heading = target.closest<HTMLElement>("#article-content h1[id], #article-content h2[id], #article-content h3[id], #article-content h4[id], #article-content h5[id], #article-content h6[id]");
      if (heading?.id) options.openHeadingAnchor(heading.id, true);
      return;
    }

    const url = new URL(anchor.href, window.location.origin);
    const isHashOnly = url.pathname === window.location.pathname && Boolean(url.hash);
    if (isHashOnly) {
      event.preventDefault();
      const headingId = safeDecodeURIComponent(url.hash.slice(1));
      if (headingId) options.openHeadingAnchor(headingId, true);
      return;
    }
    if (anchor.target || anchor.hasAttribute("download") || url.pathname.endsWith(".pdf")) return;
    if (url.origin !== window.location.origin || !ROUTE_PREFIX.test(url.pathname)) return;

    event.preventDefault();
    if (anchor.dataset.articleSlug) storageService.setSession(SessionKey.ArticleBackPath, options.currentListPath(parseRoute().lang));
    options.navigateTo(url.pathname + url.search + url.hash);
  }

}
