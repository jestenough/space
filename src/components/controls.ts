import { dom } from "../ui/dom";

export type ControlGroup = {
  searchInput: HTMLInputElement;
  sortLabel: HTMLElement;
  sizeLabel: HTMLElement;
  sortSelect: HTMLSelectElement;
  sizeSelect: HTMLSelectElement;
  pagePrev: HTMLButtonElement;
  pageInfo: HTMLElement;
  pageNext: HTMLButtonElement;
};

export const controls = {
  articles: {
    searchInput: dom.articleSearchInput,
    sortLabel: dom.sortLabel,
    sizeLabel: dom.sizeLabel,
    sortSelect: dom.sortSelect,
    sizeSelect: dom.pageSizeSelect,
    pagePrev: dom.pagePrev,
    pageInfo: dom.pageInfo,
    pageNext: dom.pageNext
  },
  tags: {
    searchInput: dom.tagSearchInput,
    sortLabel: dom.tagSortLabel,
    sizeLabel: dom.tagSizeLabel,
    sortSelect: dom.tagSortSelect,
    sizeSelect: dom.tagPageSizeSelect,
    pagePrev: dom.tagPagePrev,
    pageInfo: dom.tagPageInfo,
    pageNext: dom.tagPageNext
  }
} satisfies Record<"articles" | "tags", ControlGroup>;
