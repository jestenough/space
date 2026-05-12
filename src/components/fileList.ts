import { infoFilePath } from "@/router/routePaths";
import { SYSTEM_SECTION } from "@/core/config";
import type { InfoFileMeta } from "@/core/types";
import { pickLangText } from "@/core/languages";
import { createElement } from "@/ui/elements";

export const createInfoFileList = (lang: string, files: readonly InfoFileMeta[]): HTMLUListElement => {
  const list = createElement("ul", "info-file-tree");
  const fragment = document.createDocumentFragment();

  for (const file of files) {
    fragment.append(createInfoFileRow(lang, file));
  }

  list.append(fragment);
  return list;
};

const createInfoFileRow = (lang: string, file: InfoFileMeta): HTMLLIElement => {
  const item = createElement("li", "info-file-row");
  const link = createElement("a", "info-file-link");
  link.href = infoFilePath(lang, file.section, file.slug, file.section === SYSTEM_SECTION);
  link.dataset.infoFileSlug = file.slug;
  link.dataset.internal = "true";
  link.setAttribute("aria-label", `${file.slug}: ${pickLangText(file.description, lang)}`);

  link.append(
    createElement("span", "info-file-perms", formatFileListMeta(file)),
    document.createTextNode("  "),
    createElement("span", "info-file-name", pickLangText(file.label, lang) || file.slug)
  );
  item.append(link);
  return item;
};

const formatFileListMeta = (file: InfoFileMeta): string => {
  return `-rw-rw-r--  root  ${file.date || "----------"}`;
};
