import { articlePath } from "../routePaths";
import { text } from "../i18n";
import type { ArticleMeta, Lang } from "../types";

const make = <K extends keyof HTMLElementTagNameMap>(
  tagName: K,
  className?: string,
  textContent?: string
): HTMLElementTagNameMap[K] => {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  if (textContent !== undefined) element.textContent = textContent;
  return element;
};

type CardMetaLine = string | Array<{ className: string; text: string }>;

export function createArticleListItem(
  lang: Lang,
  article: ArticleMeta,
  viewsLabel: string,
  getViews: (slug: string) => number
): HTMLLIElement {
  const item = make("li", "article-card");
  const link = makeCardLink(articlePath(lang, article.slug), "articleSlug", article.slug, article.title[lang], [
    `${article.date} · ${article.description[lang]}`,
    article.tags.map((tag) => ({ className: "inline-tag", text: `#${tag}` })),
    `${getViews(article.slug)} ${viewsLabel}`
  ]);
  item.append(link);
  return item;
}

export function createEmptyArticleItem(lang: Lang): HTMLLIElement {
  return make("li", "meta", text(lang).noArticles);
}

function makeCardLink(
  href: string,
  datasetKey: string,
  datasetValue: string,
  title: string,
  metaLines: CardMetaLine[]
): HTMLAnchorElement {
  const link = make("a", "article-card-link article-card-full");
  link.href = href;
  link.dataset.internal = "true";
  link.dataset[datasetKey] = datasetValue;
  link.append(make("strong", undefined, title));

  for (const line of metaLines) {
    if (typeof line === "string") {
      link.append(make("div", "meta", line));
      continue;
    }

    const row = make("div", "meta tag-line");
    for (const chunk of line) {
      row.append(make("span", chunk.className, chunk.text), document.createTextNode(" "));
    }
    link.append(row);
  }

  return link;
}
