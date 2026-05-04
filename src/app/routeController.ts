import { parseRoute } from "@/router/router";
import type { Route } from "@/core/types";

export type RouteRenderOptions = { resetScroll: boolean };

export type RouteControllerDeps = {
  nextRenderId: () => number;
  currentRenderId: () => number;
  exitZenMode: () => void;
  syncRouteState: (route: Route) => void;
  applyStaticUi: (lang: string) => void;
  ensureArticlesLoaded: () => Promise<void>;
  renderNotFound: (lang: string, slug?: string) => void;
  renderArticle: (lang: string, slug: string, renderId: number) => Promise<void>;
  renderInfoFile: (lang: string, slug: string, renderId: number) => Promise<void>;
  renderIndexRoute: (lang: string) => void;
  setErrorView: () => void;
};

const routeNeedsArticleIndex = (route: Route): boolean => route.page === "articles" || route.page === "tags";

export class RouteController {
  constructor(private readonly deps: RouteControllerDeps) {}

  async render(options: RouteRenderOptions): Promise<void> {
    const renderId = this.deps.nextRenderId();
    const route = parseRoute();

    try {
      document.body.classList.remove("not-found-mode");
      if (route.page !== "article") this.deps.exitZenMode();
      this.deps.syncRouteState(route);
      this.deps.applyStaticUi(route.lang);

      if (routeNeedsArticleIndex(route)) await this.deps.ensureArticlesLoaded();
      if (renderId !== this.deps.currentRenderId()) return;

      switch (route.page) {
        case "not-found":
          this.deps.renderNotFound(route.lang, route.slug);
          break;
        case "article":
          await this.deps.renderArticle(route.lang, route.slug, renderId);
          break;
        case "info-file":
          await this.deps.renderInfoFile(route.lang, route.slug, renderId);
          break;
        default:
          this.deps.renderIndexRoute(route.lang);
      }

      if (renderId === this.deps.currentRenderId() && options.resetScroll) window.scrollTo({ top: 0, behavior: "auto" });
    } catch {
      if (renderId === this.deps.currentRenderId()) this.deps.setErrorView();
    }
  }
}
