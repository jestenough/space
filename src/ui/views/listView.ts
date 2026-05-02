import { controls } from "../../components/controls";
import type { PageModel } from "../../components/directory";
import { dom } from "../dom";
import type { ArticleMeta, Lang, TagInfo } from "../../core/types";
import { renderArticleList, renderInfoFileList, renderTagIndex } from "../view";
import type { InfoFileMeta } from "../../core/types";

export const setPagerState = (group: (typeof controls)["articles"] | (typeof controls)["tags"], page: number, totalPages: number): void => {
  group.pageInfo.textContent = `${page}/${totalPages}`;
  group.pagePrev.disabled = page <= 1;
  group.pageNext.disabled = page >= totalPages;
};

export const listView = {
  renderInfoFiles(lang: Lang, files: readonly InfoFileMeta[]): void {
    renderInfoFileList(lang, files);
  },
  renderArticles(lang: Lang, page: PageModel<ArticleMeta>, currentPage: number, title: string): void {
    renderArticleList(lang, page.items);
    dom.listTitle.textContent = title;
    setPagerState(controls.articles, currentPage, page.totalPages);
  },
  renderTags(lang: Lang, page: PageModel<TagInfo>, currentPage: number, activeTag: string, title: string): void {
    renderTagIndex(lang, page.items, activeTag);
    setPagerState(controls.tags, currentPage, page.totalPages);
    dom.articleList.replaceChildren();
    dom.listTitle.textContent = title;
    controls.articles.pageInfo.textContent = "";
    controls.articles.pagePrev.disabled = true;
    controls.articles.pageNext.disabled = true;
  }
} as const;
