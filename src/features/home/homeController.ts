import { INFO_FILES } from "../info/infoFiles";
import { text } from "../../ui/i18n";
import type { Lang } from "../../core/types";
import { setView } from "../../ui/view";
import { ViewMode } from "../../core/enums";
import { listView } from "../../ui/views/listView";

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
    document.title = "root :: " + ui.brand;
    this.deps.updateSeo(lang, ui.welcomeTitle, ui.welcomeBody);
    this.deps.updateRightProcess(lang);
    setView(ViewMode.List);
  }
}
