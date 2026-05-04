import { dom } from "@/ui/dom";
import { articlesPath, homePath, tagPath } from "@/router/routePaths";
import { pdfService } from "@/services/pdfService";
import { articleTitle } from "@/services/articleService";
import type { ArticleMeta, Lang } from "@/core/types";

const normalizeHeadingText = (value: string): string => value.replace(/#$/, "").replace(/\s+/g, " ").trim().toLowerCase();

const makeInlineLink = (href: string, label: string, options: { newTab?: boolean } = {}): HTMLAnchorElement => {
  const link = document.createElement("a");
  link.href = href;
  link.textContent = label;
  if (options.newTab) {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  } else {
    link.dataset.internal = "true";
  }
  return link;
};

const removeDuplicateArticleHeading = (title: string): void => {
  const firstHeading = dom.articleContent.querySelector<HTMLElement>("h1:first-child, h2:first-child");
  if (!firstHeading) return;
  if (normalizeHeadingText(firstHeading.textContent ?? "") === normalizeHeadingText(title)) firstHeading.remove();
};

const appendArticleLinks = (lang: Lang, article: ArticleMeta): void => {
  const topNav = document.createElement("nav");
  topNav.className = "article-breadcrumbs";
  topNav.setAttribute("aria-label", "Breadcrumbs");

  const current = document.createElement("span");
  current.textContent = article.slug;
  topNav.append(
    makeInlineLink(homePath(lang), "root"),
    document.createTextNode(" / "),
    makeInlineLink(articlesPath(lang), "articles"),
    document.createTextNode(" / "),
    current
  );

  const bottomNav = document.createElement("nav");
  bottomNav.className = "article-seo-links";
  bottomNav.setAttribute("aria-label", "Article links");

  const tags = document.createElement("p");
  tags.className = "article-tag-links";
  tags.append(document.createTextNode("tags: "));
  for (const tag of article.tags) tags.append(makeInlineLink(tagPath(lang, tag), `#${tag}`), document.createTextNode(" "));

  const files = document.createElement("p");
  files.className = "article-file-links";
  files.append(makeInlineLink(pdfService.articlePdfPath(lang, article.slug), "download PDF", { newTab: true }));

  const neighbors = document.createElement("p");
  neighbors.className = "article-neighbor-links";
  if (article.prev) neighbors.append(makeInlineLink(article.prev.path, `previous: ${article.prev.title}`));
  if (article.prev && article.next) neighbors.append(document.createTextNode(" · "));
  if (article.next) neighbors.append(makeInlineLink(article.next.path, `next: ${article.next.title}`));

  bottomNav.append(tags, files);
  if (article.prev || article.next) bottomNav.append(neighbors);

  dom.articleContent.prepend(topNav);
  dom.articleContent.append(bottomNav);
};

export const articleView = {
  renderHtml(html: string): void {
    dom.articleContent.innerHTML = html;
  },
  finalize(lang: Lang, article: ArticleMeta): void {
    removeDuplicateArticleHeading(articleTitle(article, lang));
    appendArticleLinks(lang, article);
  }
} as const;
