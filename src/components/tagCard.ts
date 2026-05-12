import { tagPath } from "@/router/routePaths";
import type { TagInfo } from "@/core/types";
import { createElement } from "@/ui/elements";

export const createTagListItem = (lang: string, tag: TagInfo, activeTag: string): HTMLLIElement => {
  const item = createElement("li", "tag-card");
  const link = createElement("a", `tag-row ${activeTag === tag.name ? "is-active" : ""}`);
  link.href = tagPath(lang, tag.name);
  link.dataset.tag = tag.name;
  link.dataset.internal = "true";
  link.append(
    createElement("span", "tag-name", `#${tag.name}`),
    createElement("span", "tag-count", `${tag.count} file${tag.count === 1 ? "" : "s"}`)
  );
  item.append(link);
  return item;
};
