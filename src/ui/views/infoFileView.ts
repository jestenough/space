import { dom } from "@/ui/dom";

export const infoFileView = {
  renderHtml(html: string): void {
    dom.articleContent.innerHTML = html;
  }
} as const;
