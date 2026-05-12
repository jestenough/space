import { infoFileOpenCommand, shellCommandMarkup } from "@/components/shell";
import { dom } from "@/ui/dom";
import { label, text } from "@/ui/i18n";
import { findInfoFile, renderInfoFileHtml } from "@/features/info/infoFiles";
import type { InfoFileMeta, Lang } from "@/core/types";
import { setView } from "@/ui/view";
import { ViewMode } from "@/core/enums";
import { infoFileView } from "@/ui/views/infoFileView";
import { missingTranslationCopy } from "@/ui/missingTranslation";

type InfoFileRenderContext = { infoFile?: InfoFileMeta };

export type InfoFileControllerDeps = {
  currentRenderId: () => number;
  renderNotFound: (lang: Lang, slug?: string) => void;
  setSectionContext: (section: string) => void;
  setActiveInfoFile: (file: InfoFileMeta | null) => void;
  applyPanelState: (lang: Lang) => void;
  renderArticleToc: () => void;
  setFileDownloadVisible: (file: InfoFileMeta | null) => void;
  applyWelcomeText: (title: string, lead: string, body?: string) => void;
  updateSeo: (lang: Lang, title: string, description: string, indexable?: boolean) => void;
  updateRightProcess: (lang: Lang, context?: InfoFileRenderContext) => void;
};

export class InfoFileController {
  constructor(private readonly deps: InfoFileControllerDeps) {}

  async render(lang: Lang, section: string, slug: string, renderId: number): Promise<void> {
    const file = await findInfoFile(section, slug);
    if (!file) {
      this.deps.renderNotFound(lang, slug);
      return;
    }

    const html = await renderInfoFileHtml(file, lang);
    if (renderId !== this.deps.currentRenderId()) return;

    this.deps.setSectionContext(file.section);
    this.deps.setActiveInfoFile(file);
    this.deps.applyPanelState(lang);
    infoFileView.renderHtml(html);
    this.deps.renderArticleToc();
    const translated = file.languages.includes(lang);
    this.deps.setFileDownloadVisible(translated && file.downloadPath ? file : null);
    const fallback = missingTranslationCopy(lang);
    const title = translated ? label(file.title, lang) : fallback.title;
    const description = translated ? label(file.description, lang) : fallback.description;
    this.deps.applyWelcomeText(title, description);
    dom.renderIndicator.innerHTML = shellCommandMarkup(infoFileOpenCommand(file.section, file.slug));
    document.title = title + " :: " + text(lang).brand;
    this.deps.updateSeo(lang, title, description, translated);
    this.deps.updateRightProcess(lang, { infoFile: file });
    setView(ViewMode.Article);
  }
}
