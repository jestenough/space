import { INFO_FILES } from "@/features/info/infoFiles";
import { text } from "@/ui/i18n";
import { siteMetaService } from "@/services/siteMetaService";
import type { Lang } from "@/core/types";
import { setView } from "@/ui/view";
import { ViewMode } from "@/core/enums";
import { listView } from "@/ui/views/listView";

export type HomeControllerDeps = {
  applyPanelState: (lang: Lang) => void;
  updateSeo: (lang: Lang, title: string, description: string, indexable?: boolean) => void;
  updateRightProcess: (lang: Lang) => void;
};

export class HomeController {
  constructor(private readonly deps: HomeControllerDeps) {}

  render(lang: Lang): void {
    const ui = text(lang);
    this.deps.applyPanelState(lang);
    listView.renderInfoFiles(lang, INFO_FILES);
    const meta = siteMetaService.pageMeta("home", lang);
    document.title = `${meta.title} :: ${ui.brand}`;
    this.deps.updateSeo(lang, meta.title, meta.description);
    this.deps.updateRightProcess(lang);
    setView(ViewMode.List);
  }
}
