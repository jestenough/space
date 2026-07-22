import { storageService } from "@/services/storageService";

const DESKTOP_QUERY = "(min-width: 761px)";
const panelStorageKey = (key: string): string => `panel:${key}:open`;

type Placement = {
  element: HTMLElement;
  parent: Node;
  nextSibling: Node | null;
  mobileParent: HTMLElement;
};

const placement = (element: HTMLElement | null, mobileParent: HTMLElement | null): Placement | null => {
  if (!element?.parentNode || !mobileParent) return null;
  return { element, parent: element.parentNode, nextSibling: element.nextSibling, mobileParent };
};

const restore = ({ element, parent, nextSibling }: Placement): void => {
  if (element.parentNode === parent && element.nextSibling === nextSibling) return;
  parent.insertBefore(element, nextSibling?.parentNode === parent ? nextSibling : null);
};

const moveToMobile = ({ element, mobileParent }: Placement): void => {
  if (element.parentNode === mobileParent) return;
  mobileParent.append(element);
};

export const panelController = {
  init(): void {
    const media = window.matchMedia(DESKTOP_QUERY);
    const panels = Array.from(document.querySelectorAll<HTMLDetailsElement>("details[data-panel-key]"));
    const defaults = new Map(panels.map((panel) => [panel, panel.open]));
    const contentsButton = document.querySelector<HTMLElement>('[data-mobile-overlay-open="contents"]');
    const placements = [
      placement(document.querySelector<HTMLElement>(".nav-window"), document.querySelector<HTMLElement>("[data-mobile-sections-body]")),
      placement(document.querySelector<HTMLElement>(".session-window"), document.querySelector<HTMLElement>("[data-mobile-options-body]")),
      placement(document.getElementById("toc-panel"), document.querySelector<HTMLElement>("[data-mobile-contents-body]")),
    ].filter((value): value is Placement => value !== null);

    const applyLayout = (): void => {
      this.close();
      const desktop = media.matches;
      placements.forEach((item) => {
        const isToc = item.element.id === "toc-panel";
        if (desktop || (isToc && item.element.classList.contains("hidden"))) restore(item);
        else moveToMobile(item);
      });
      contentsButton?.classList.toggle("hidden", document.getElementById("toc-panel")?.classList.contains("hidden") ?? true);
      panels.forEach((panel) => {
        const key = panel.dataset.panelKey;
        if (!key) return;
        panel.open = desktop
          ? storageService.getBoolean(panelStorageKey(key)) ?? defaults.get(panel) ?? false
          : key !== "systemnote";
      });
      document.body.dataset.mobileOverlays = "ready";
    };

    panels.forEach((panel) => {
      const key = panel.dataset.panelKey;
      if (!key) return;
      panel.addEventListener("toggle", () => {
        if (media.matches) storageService.setBoolean(panelStorageKey(key), panel.open);
      });
    });
    document.querySelectorAll<HTMLButtonElement>("[data-mobile-overlay-open]").forEach((button) => {
      button.addEventListener("click", () => this.open(button.dataset.mobileOverlayOpen || ""));
    });
    document.querySelectorAll<HTMLElement>("[data-mobile-overlay-close]").forEach((control) => {
      control.addEventListener("click", () => this.close());
    });
    media.addEventListener("change", applyLayout);
    applyLayout();
  },

  open(name: string): void {
    if (!name) return;
    this.close();
    document.getElementById("mobile-overlay-backdrop")?.classList.remove("hidden");
    document.querySelector<HTMLElement>(`[data-mobile-overlay="${name}"]`)?.classList.remove("hidden");
  },

  close(): void {
    document.getElementById("mobile-overlay-backdrop")?.classList.add("hidden");
    document.querySelectorAll<HTMLElement>("[data-mobile-overlay]").forEach((overlay) => overlay.classList.add("hidden"));
  },
} as const;
