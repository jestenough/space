import { infoFilePath } from "../routePaths";
import type { InfoFileMeta, Lang } from "../types";

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

export function createInfoFileList(lang: Lang, files: readonly InfoFileMeta[]): HTMLUListElement {
  const list = make("ul", "info-file-tree");
  const fragment = document.createDocumentFragment();

  for (const file of files) {
    fragment.append(createInfoFileRow(lang, file));
  }

  list.append(fragment);
  return list;
}

function createInfoFileRow(lang: Lang, file: InfoFileMeta): HTMLLIElement {
  const item = make("li", "info-file-row");
  const link = make("a", "info-file-link");
  link.href = infoFilePath(lang, file.routeSlug);
  link.dataset.infoFileSlug = file.slug;
  link.dataset.internal = "true";
  link.setAttribute("aria-label", `${file.slug}: ${file.description[lang]}`);

  link.append(
    make("span", "info-file-perms", formatFileListMeta(file)),
    document.createTextNode("  "),
    make("span", "info-file-name", file.slug)
  );
  item.append(link);
  return item;
}

function formatFileListMeta(file: InfoFileMeta): string {
  return `${file.permissions}  ${file.owner.padEnd(4, " ")}  ${file.modified}`;
}
