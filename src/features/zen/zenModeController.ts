import { CssClass } from "@/core/enums";

const state = { topHover: false };

export const zenModeController = {
  enter(contentRoot: HTMLElement, isAllowed: boolean): void {
    if (!isAllowed) return;
    document.body.classList.add(CssClass.ZenMode);
    contentRoot.tabIndex = -1;
    contentRoot.focus({ preventScroll: true });
  },
  exit(): void {
    document.body.classList.remove(CssClass.ZenMode, CssClass.ZenTopHover);
    state.topHover = false;
  },
  bindEmptyAreaExit(contentRoot: HTMLElement): () => void {
    const handler = (event: MouseEvent): void => {
      if (!document.body.classList.contains(CssClass.ZenMode)) return;
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.closest("a, button, input, select, textarea, img, figure, pre, code, math, p, li, h1, h2, h3, h4, h5, h6")) return;
      if (target === contentRoot || contentRoot.contains(target) || target === document.body || target === document.documentElement) this.exit();
    };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  },
  bindTopHover(): () => void {
    const handler = (event: MouseEvent): void => {
      if (!document.body.classList.contains(CssClass.ZenMode)) return;
      const nextHover = event.clientY < 76;
      if (nextHover === state.topHover) return;
      state.topHover = nextHover;
      document.body.classList.toggle(CssClass.ZenTopHover, nextHover);
    };
    document.addEventListener("mousemove", handler, { passive: true });
    return () => document.removeEventListener("mousemove", handler);
  }
} as const;
