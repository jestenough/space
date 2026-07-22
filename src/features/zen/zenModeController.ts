import { CssClass } from "@/core/enums";

const state: {
  topHover: boolean;
  topHoverHandler: ((event: MouseEvent) => void) | null;
  emptyAreaHandler: ((event: MouseEvent) => void) | null;
} = {
  topHover: false,
  topHoverHandler: null,
  emptyAreaHandler: null,
};

const bindTopHover = (): void => {
  if (state.topHoverHandler) return;
  state.topHoverHandler = (event: MouseEvent): void => {
    const nextHover = event.clientY < 76;
    if (nextHover === state.topHover) return;
    state.topHover = nextHover;
    document.body.classList.toggle(CssClass.ZenTopHover, nextHover);
  };
  document.addEventListener("mousemove", state.topHoverHandler, { passive: true });
};

const unbindTopHover = (): void => {
  if (!state.topHoverHandler) return;
  document.removeEventListener("mousemove", state.topHoverHandler);
  state.topHoverHandler = null;
};

const unbindEmptyAreaExit = (): void => {
  if (!state.emptyAreaHandler) return;
  document.removeEventListener("click", state.emptyAreaHandler);
  state.emptyAreaHandler = null;
};

const exitZen = (): void => {
  document.body.classList.remove(CssClass.ZenMode, CssClass.ZenTopHover);
  unbindTopHover();
  unbindEmptyAreaExit();
  state.topHover = false;
};

const bindEmptyAreaExit = (contentRoot: HTMLElement): void => {
  if (state.emptyAreaHandler) return;
  state.emptyAreaHandler = (event: MouseEvent): void => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.closest("a, button, input, select, textarea, img, figure, pre, code, math, p, li, h1, h2, h3, h4, h5, h6")) return;
    if (target === contentRoot || contentRoot.contains(target) || target === document.body || target === document.documentElement) {
      exitZen();
    }
  };
  document.addEventListener("click", state.emptyAreaHandler);
};

export const zenModeController = {
  enter(contentRoot: HTMLElement): void {
    document.body.classList.add(CssClass.ZenMode);
    bindTopHover();
    bindEmptyAreaExit(contentRoot);
    contentRoot.tabIndex = -1;
    contentRoot.focus({ preventScroll: true });
  },
  exit: exitZen,
} as const;
