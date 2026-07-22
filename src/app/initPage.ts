import { StorageKey } from "@/core/enums";
import { DEFAULT_LANG, normalizeLang } from "@/core/languages";
import { safeDecodeURIComponent } from "@/core/url";
import { initActions } from "@/features/actions/actionController";
import { initCitations } from "@/features/citations/citationController";
import { clipboardController } from "@/features/clipboard/clipboardController";
import { imageViewerController } from "@/features/content/imageViewerController";
import { ListController } from "@/features/lists/listController";
import { panelController } from "@/features/panels/panelController";
import { initTocEnhancer, scrollToHeading } from "@/features/toc/tocEnhancer";
import { zenModeController } from "@/features/zen/zenModeController";
import { storageService } from "@/services/storageService";
import { themeService } from "@/services/themeService";

const sameDocumentHash = (url: URL): boolean => url.pathname === window.location.pathname
  && url.search === window.location.search
  && Boolean(url.hash);

const visibleSearchInput = (): HTMLInputElement | null => Array.from(
  document.querySelectorAll<HTMLInputElement>("[data-list-search]")
).find((input) => !input.closest(".hidden")) ?? null;

const initTheme = (): void => {
  const switcher = document.getElementById("theme-switcher") as HTMLSelectElement | null;
  const initial = themeService.current();
  const stored = storageService.get(StorageKey.Theme);
  const active = stored && stored !== initial ? themeService.apply(stored) : initial;
  if (switcher) switcher.value = active;
  switcher?.addEventListener("change", () => {
    const theme = themeService.apply(switcher.value);
    storageService.set(StorageKey.Theme, theme);
  });
  themeService.bindSystemTheme(() => {
    if (document.documentElement.dataset.themeChoice === "system") themeService.apply("system");
  });
};

const initLanguage = (): void => {
  const switcher = document.getElementById("lang-switcher") as HTMLSelectElement | null;
  if (!switcher) return;
  switcher.value = document.documentElement.lang || DEFAULT_LANG;
  switcher.addEventListener("change", () => {
    const lang = normalizeLang(switcher.value);
    storageService.set(StorageKey.Lang, lang);
    const alternate = Array.from(document.querySelectorAll<HTMLLinkElement>('link[rel="alternate"][hreflang]'))
      .find((link) => link.hreflang === lang);
    if (alternate) {
      const url = new URL(alternate.href, window.location.origin);
      window.location.assign(`${url.pathname}${url.search}${url.hash}`);
      return;
    }
    const localizedPath = window.location.pathname.replace(/^\/[a-z]{2,3}(?:-[A-Z]{2})?/, "");
    window.location.assign(`/${lang}${localizedPath}${window.location.search}${window.location.hash}`);
  });
};

const initLists = (): void => {
  document.querySelectorAll<HTMLElement>("[data-list-root]").forEach((root) => {
    new ListController(root).init();
  });
};

const initImageViewer = (): void => {
  const root = document.querySelector<HTMLElement>("[data-file-content]");
  if (root?.querySelector("img[data-zoomable-image]")) imageViewerController.bind(root);
};

const initZenMode = (): void => {
  const root = document.querySelector<HTMLElement>("[data-file-content]");
  const enter = document.querySelector<HTMLButtonElement>("[data-zen-toggle]");
  const exit = document.querySelector<HTMLButtonElement>("[data-zen-exit]");
  if (!root || !enter) return;
  enter.addEventListener("click", () => zenModeController.enter(root));
  exit?.addEventListener("click", () => zenModeController.exit());
};

const initDocumentNavigation = (): void => {
  document.addEventListener("click", (event) => {
    if (event.defaultPrevented) return;
    const anchor = (event.target as HTMLElement | null)?.closest<HTMLAnchorElement>('a[href^="#"], a[data-heading-id]');
    if (!anchor) return;
    const url = new URL(anchor.href, window.location.origin);
    if (!sameDocumentHash(url)) return;
    const id = safeDecodeURIComponent(url.hash.slice(1));
    if (!id) return;
    event.preventDefault();
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.search}#${encodeURIComponent(id)}`);
    scrollToHeading(id);
  });
};

const initKeyboard = (): void => {
  document.addEventListener("keydown", (event) => {
    if (event.key !== "/" && event.key !== "Escape") return;
    const typing = event.target instanceof HTMLElement
      && event.target.matches("input, textarea, select, [contenteditable='true']");
    if (!typing && event.key === "/") {
      event.preventDefault();
      visibleSearchInput()?.focus();
    }
    if (event.key === "Escape") {
      zenModeController.exit();
      panelController.close();
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    }
  });
};

export const initPage = (): void => {
  initTheme();
  initLanguage();
  initActions();
  clipboardController.init();
  initLists();
  initTocEnhancer();
  initImageViewer();
  initZenMode();
  panelController.init();
  initDocumentNavigation();
  initKeyboard();
  const contentRoot = document.querySelector<HTMLElement>("[data-file-content]");
  if (contentRoot) initCitations(contentRoot);
};
