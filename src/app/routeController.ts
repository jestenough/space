import { parseRoute } from "@/router/router";
import type { Route } from "@/core/types";

export type RouteRenderOptions = { resetScroll: boolean };

export type RouteControllerDeps = {
  nextRenderId: () => number;
  currentRenderId: () => number;
  exitZenMode: () => void;
  syncRouteState: (route: Route) => void;
  applyStaticUi: (lang: string) => void;
  ensureSectionLoaded: (section: string) => Promise<void>;
  renderNotFound: (lang: string, slug?: string) => void;
  renderArticle: (lang: string, slug: string, renderId: number) => Promise<void>;
  renderInfoFile: (lang: string, section: string, slug: string, renderId: number) => Promise<void>;
  renderIndexRoute: (lang: string) => void;
  setErrorView: () => void;
};

const routeSection = (route: Route): string | null => {
  if (route.page === "section") return route.section;
  if (route.page === "info-file") return route.section;
  if (route.page === "articles" || route.page === "article" || route.page === "tags") return "articles";
  return null;
};

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

      const section = routeSection(route);
      if (section) await this.deps.ensureSectionLoaded(section);
      if (renderId !== this.deps.currentRenderId()) return;

      switch (route.page) {
        case "not-found":
          this.deps.renderNotFound(route.lang, route.slug);
          break;
        case "article":
          await this.deps.renderArticle(route.lang, route.slug, renderId);
          break;
        case "info-file":
          await this.deps.renderInfoFile(route.lang, route.section, route.slug, renderId);
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
