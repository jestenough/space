import { text } from "@/ui/i18n";
import { label } from "@/ui/i18n";
import type { InfoFileMeta, Lang, SectionMeta } from "@/core/types";
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

  render(lang: Lang, files: readonly InfoFileMeta[], section: SectionMeta): void {
    const ui = text(lang);
    this.deps.applyPanelState(lang);
    listView.renderInfoFiles(lang, files);
    const title = label(section.title, lang);
    const description = label(section.description, lang);
    document.title = `${title} :: ${ui.brand}`;
    this.deps.updateSeo(lang, title, description);
    this.deps.updateRightProcess(lang);
    setView(ViewMode.List);
  }
}
