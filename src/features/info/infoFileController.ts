import { infoFileOpenCommand } from "../../components/shell";
import { dom } from "../../ui/dom";
import { label, text } from "../../ui/i18n";
import { findInfoFile, renderInfoFileHtml } from "./infoFiles";
import type { InfoFileMeta, Lang } from "../../core/types";
import { setView } from "../../ui/view";
import { ViewMode } from "../../core/enums";
import { infoFileView } from "../../ui/views/infoFileView";

type InfoFileRenderContext = { infoFile?: InfoFileMeta };

export type InfoFileControllerDeps = {
  currentRenderId: () => number;
  renderNotFound: (lang: Lang, slug?: string) => void;
  setRootContext: () => void;
  setActiveInfoFile: (file: InfoFileMeta | null) => void;
  applyPanelState: (lang: Lang) => void;
  renderArticleToc: () => void;
  setArticleActionsVisible: (isVisible: boolean) => void;
  applyWelcomeText: (title: string, lead: string, body?: string) => void;
  updateSeo: (lang: Lang, title: string, description: string, indexable?: boolean) => void;
  updateRightProcess: (lang: Lang, context?: InfoFileRenderContext) => void;
};

export class InfoFileController {
  constructor(private readonly deps: InfoFileControllerDeps) {}

  async render(lang: Lang, slug: string, renderId: number): Promise<void> {
    const file = findInfoFile(slug);
    if (!file) {
      this.deps.renderNotFound(lang, slug);
      return;
    }

    const html = await renderInfoFileHtml(file, lang);
    if (renderId !== this.deps.currentRenderId()) return;

    this.deps.setRootContext();
    this.deps.setActiveInfoFile(file);
    this.deps.applyPanelState(lang);
    infoFileView.renderHtml(html);
    this.deps.renderArticleToc();
    this.deps.setArticleActionsVisible(false);
    this.deps.applyWelcomeText(label(file.title, lang), label(file.description, lang));
    dom.renderIndicator.textContent = infoFileOpenCommand(file.slug);
    document.title = label(file.title, lang) + " :: " + text(lang).brand;
    this.deps.updateSeo(lang, label(file.title, lang), label(file.description, lang));
    this.deps.updateRightProcess(lang, { infoFile: file });
    setView(ViewMode.Article);
  }
}
