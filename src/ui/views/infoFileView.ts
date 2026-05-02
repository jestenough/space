import { dom } from "../dom";

export const infoFileView = {
  renderHtml(html: string): void {
    dom.articleContent.innerHTML = html;
  }
} as const;
