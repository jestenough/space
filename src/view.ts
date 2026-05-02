import { dom } from "./dom";
import { createArticleListItem, createEmptyArticleItem } from "./components/articleCard";
import { createInfoFileList } from "./components/fileList";
import { createTagListItem } from "./components/tagCard";
import type { ArticleMeta, InfoFileMeta, Lang, TagInfo } from "./types";

const clear = (element: Element): void => {
  element.replaceChildren();
};

export function setView(view: "list" | "article" | "error"): void {
  dom.listView.classList.toggle("hidden", view !== "list");
  dom.articleView.classList.toggle("hidden", view !== "article");
  dom.errorView.classList.toggle("hidden", view !== "error");
}

export function renderTagIndex(lang: Lang, tags: TagInfo[], activeTag: string): void {
  clear(dom.tagList);
  const fragment = document.createDocumentFragment();
  for (const tag of tags) fragment.append(createTagListItem(lang, tag, activeTag));
  dom.tagList.append(fragment);
}

export function renderArticleList(
  lang: Lang,
  articles: ArticleMeta[],
  viewsLabel: string,
  getViews: (slug: string) => number
): void {
  clear(dom.articleList);

  if (articles.length === 0) {
    dom.articleList.append(createEmptyArticleItem(lang));
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const article of articles) fragment.append(createArticleListItem(lang, article, viewsLabel, getViews));
  dom.articleList.append(fragment);
}

export function renderInfoFileList(lang: Lang, files: readonly InfoFileMeta[]): void {
  clear(dom.homeFilesPanel);
  dom.homeFilesPanel.append(createInfoFileList(lang, files));
}

export function renderArticleContent(html: string): void {
  dom.articleContent.innerHTML = html;
}
