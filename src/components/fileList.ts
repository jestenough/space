import { infoFilePath } from "@/router/routePaths";
import type { InfoFileMeta } from "@/core/types";
import { pickLangText } from "@/core/languages";

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

export const createInfoFileList = (lang: string, files: readonly InfoFileMeta[]): HTMLUListElement => {
  const list = make("ul", "info-file-tree");
  const fragment = document.createDocumentFragment();

  for (const file of files) {
    fragment.append(createInfoFileRow(lang, file));
  }

  list.append(fragment);
  return list;
};

const createInfoFileRow = (lang: string, file: InfoFileMeta): HTMLLIElement => {
  const item = make("li", "info-file-row");
  const link = make("a", "info-file-link");
  link.href = infoFilePath(lang, file.section, file.slug, file.section === "site");
  link.dataset.infoFileSlug = file.slug;
  link.dataset.internal = "true";
  link.setAttribute("aria-label", `${file.slug}: ${pickLangText(file.description, lang)}`);

  link.append(
    make("span", "info-file-perms", formatFileListMeta(file)),
    document.createTextNode("  "),
    make("span", "info-file-name", pickLangText(file.label, lang) || file.slug)
  );
  item.append(link);
  return item;
};

const formatFileListMeta = (file: InfoFileMeta): string => {
  return `-rw-rw-r--  root  ${file.date || "----------"}`;
};
