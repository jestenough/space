import { text } from "@/ui/i18n";
import { dom } from "@/ui/dom";
import { setView } from "@/ui/view";
import { escapeHtml } from "@/core/escape";
import { CssClass, ViewMode } from "@/core/enums";
import type { Lang } from "@/core/types";
import { shellCommandMarkup, shellCommandText } from "@/components/shell";
import { homePath } from "@/router/routePaths";

export const notFoundView = {
  render(lang: Lang, path: string): void {
    const root = homePath(lang);
    document.body.classList.add(CssClass.NotFoundMode);
    dom.quickNav.querySelectorAll(".quick-link").forEach((link) => link.classList.remove(CssClass.Active));
    dom.welcomeCommand.innerHTML = shellCommandMarkup(shellCommandText("dmesg | tail -2"));
    dom.welcomeTitle.textContent = "signal lost";
    dom.welcomeLead.textContent = "cd /";
    dom.welcomeBody.textContent = "";
    dom.errorTitle.textContent = "signal lost";
    dom.errorText.innerHTML = `<a class="error-root-link" href="${root}" data-internal="true" aria-label="cd /">cd /</a>`;
    dom.renderIndicator.innerHTML = shellCommandMarkup(shellCommandText("dmesg | grep ENOENT"));
    document.title = "signal lost :: " + text(lang).brand;
    dom.processLog.innerHTML = [
      shellCommandMarkup(shellCommandText("dmesg | tail -4")),
      '<span class="meta-rule" aria-hidden="true"></span>',
      '<span class="meta-key">errno</span>: ENOENT',
      '<span class="meta-key">route</span>: ' + escapeHtml(path),
      '<span class="meta-key">signal</span>: lost',
      `<span class="meta-key">recovery</span>: <a class="meta-tag-link" href="${root}" data-internal="true">cd /</a>`,
    ].join("<br>");
    setView(ViewMode.Error);
  }
} as const;
