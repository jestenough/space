import { StorageKey } from "@/core/enums";
import { DEFAULT_LANG, normalizeLang } from "@/core/languages";
import { safeDecodeURIComponent } from "@/core/url";
import { contentCopyController } from "@/features/content/contentCopyController";
import { ListController } from "@/features/lists/listController";
import { initTocEnhancer, scrollToHeading } from "@/features/toc/tocEnhancer";
import { zenModeController } from "@/features/zen/zenModeController";
import { storageService } from "@/services/storageService";
import { themeService } from "@/services/themeService";

const sameDocumentHash = (url: URL): boolean => url.pathname === window.location.pathname && url.search === window.location.search && Boolean(url.hash);
const visibleSearchInput = (): HTMLInputElement | null => Array.from(document.querySelectorAll<HTMLInputElement>("[data-list-search]"))
  .find((input) => !input.closest(".hidden")) ?? null;

export class PageController {
  init(): void {
    this.initTheme();
    this.initLanguage();
    this.initActionButtons();
    this.initLists();
    this.initToc();
    this.initCopy();
    this.initZenMode();
    this.initDocumentNavigation();
    this.initKeyboard();
  }

  private initTheme(): void {
    const themeSwitcher = document.getElementById("theme-switcher") as HTMLSelectElement | null;
    const initialTheme = themeService.initBeforeRender();
    const activeTheme = themeService.apply(storageService.get(StorageKey.Theme) ?? initialTheme);
    storageService.set(StorageKey.Theme, activeTheme);
    if (themeSwitcher) themeSwitcher.value = activeTheme;
    themeSwitcher?.addEventListener("change", () => {
      const theme = themeService.apply(themeSwitcher.value);
      storageService.set(StorageKey.Theme, theme);
    });
    themeService.bindSystemTheme(() => {
      if (document.documentElement.dataset.themeChoice === "system") themeService.apply("system");
    });
  }

  private initLanguage(): void {
    const langSwitcher = document.getElementById("lang-switcher") as HTMLSelectElement | null;
    if (!langSwitcher) return;
    langSwitcher.value = document.documentElement.lang || DEFAULT_LANG;
    langSwitcher.addEventListener("change", () => {
      const lang = normalizeLang(langSwitcher.value);
      storageService.set(StorageKey.Lang, lang);
      const alternates = new Map(
        Array.from(document.querySelectorAll<HTMLLinkElement>('link[rel="alternate"][hreflang]')).map((link) => [link.hreflang, link])
      );
      const alternate = alternates.get(lang);
      if (alternate) {
        const url = new URL(alternate.href, window.location.origin);
        window.location.assign(`${url.pathname}${url.search}${url.hash}`);
        return;
      }

      const fallback = `/${lang}${window.location.pathname.replace(/^\/[a-z]{2,3}(?:-[A-Z]{2})?/, "") || ""}${window.location.search}${window.location.hash}`;
      window.location.assign(fallback);
    });
  }

  private initActionButtons(): void {
    document.querySelectorAll<HTMLButtonElement>("button[data-action-href]").forEach((button) => {
      button.addEventListener("click", () => {
        const href = button.dataset.actionHref;
        if (!href) return;
        const target = button.dataset.actionTarget === "_blank" ? "_blank" : "_self";
        if (target === "_blank") window.open(href, "_blank", "noopener,noreferrer");
        else window.location.assign(href);
      });
    });
  }

  private initLists(): void {
    document.querySelectorAll<HTMLElement>("[data-list-root]").forEach((root) => {
      new ListController(root).init();
    });
  }

  private initToc(): void {
    initTocEnhancer();
  }

  private initCopy(): void {
    const contentRoot = document.querySelector<HTMLElement>("[data-file-content]");
    if (contentRoot) contentCopyController.bind(contentRoot);
  }

  private initZenMode(): void {
    const contentRoot = document.querySelector<HTMLElement>("[data-file-content]");
    const enterButton = document.querySelector<HTMLButtonElement>("[data-zen-toggle]");
    const exitButton = document.getElementById("zen-exit-btn") as HTMLButtonElement | null;
    if (!contentRoot) return;
    enterButton?.addEventListener("click", () => zenModeController.enter(contentRoot, true));
    exitButton?.addEventListener("click", () => zenModeController.exit());
    zenModeController.bindTopHover();
  }

  private initDocumentNavigation(): void {
    document.addEventListener("click", (event) => {
      const target = event.target as HTMLElement | null;
      const anchor = target?.closest<HTMLAnchorElement>('a[href^="#"], a[data-heading-id]');
      if (!anchor) return;
      const url = new URL(anchor.href, window.location.origin);
      if (!sameDocumentHash(url)) return;
      const id = safeDecodeURIComponent(url.hash.slice(1));
      if (!id) return;
      event.preventDefault();
      window.history.replaceState({}, "", `${window.location.pathname}${window.location.search}#${encodeURIComponent(id)}`);
      scrollToHeading(id);
    });
  }

  private initKeyboard(): void {
    document.addEventListener("keydown", (event) => {
      const typing = event.target instanceof HTMLElement && event.target.matches("input, textarea, select, [contenteditable='true']");
      if (!typing && event.key === "/") {
        event.preventDefault();
        visibleSearchInput()?.focus();
      }
      if (event.key === "Escape") {
        zenModeController.exit();
        if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
      }
    });
  }
}
