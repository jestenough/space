import { articleDescription, articleTitle } from "../features/articles/articles";
import { articlePath } from "../router/routePaths";
import { text } from "../ui/i18n";
import type { ArticleMeta, Lang } from "../core/types";

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

export const createArticleListItem = (lang: Lang, article: ArticleMeta): HTMLLIElement => {
  const item = make("li", "article-card");
  const link = makeCardLink(articlePath(lang, article.slug), "articleSlug", article.slug, articleTitle(article, lang), [
    `${article.date} · ${articleDescription(article, lang)}`,
    article.tags.map((tag) => ({ className: "inline-tag", text: `#${tag}` }))
  ]);
  item.append(link);
  return item;
};

export const createEmptyArticleItem = (lang: Lang): HTMLLIElement => make("li", "meta", text(lang).noArticles);

const makeCardLink = (
  href: string,
  datasetKey: string,
  datasetValue: string,
  title: string,
  metaLines: CardMetaLine[]
): HTMLAnchorElement => {
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
    for (const chunk of line) row.append(make("span", chunk.className, chunk.text), document.createTextNode(" "));
    link.append(row);
  }

  return link;
};
