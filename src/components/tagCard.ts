import { tagPath } from "../routePaths";
import type { Lang, TagInfo } from "../types";

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

export function createTagListItem(lang: Lang, tag: TagInfo, activeTag: string): HTMLLIElement {
  const item = make("li", "tag-card");
  const link = make("a", `tag-row ${activeTag === tag.name ? "is-active" : ""}`);
  link.href = tagPath(lang, tag.name);
  link.dataset.tag = tag.name;
  link.dataset.internal = "true";
  link.append(
    make("span", "tag-name", `#${tag.name}`),
    make("span", "tag-count", `${tag.count} file${tag.count === 1 ? "" : "s"}`)
  );
  item.append(link);
  return item;
}
